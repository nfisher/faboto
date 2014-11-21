import re
from fabric.api import *
from time import gmtime, strftime, time
from os import stat
from os.path import dirname, abspath, isfile
from boto.s3.key import Key
from boto import connect_s3
from boto.s3.connection import Location

PUPPET_BUCKET = 'jbx-puppet'

env.start_time = time()

def revision():
    """
    Get the current revision from HEAD (implies mainline development only).
    """
    with lcd(dirname(abspath(__file__))):
        revision = local('git rev-parse HEAD', capture=True).rstrip()
    return revision


def unpack():
    """
    Upload and unpack the assets on the target server(s).
    """
    # TODO: (NF 2012-12-06) Use a folder other than /tmp for the upload for security.
    rev = revision()

    with lcd(dirname(abspath(__file__))):
        put('pkg/puppet-{0}.tar.gz'.format(rev), '/root', use_sudo=True)
        put('puppet/unpack.sh', '/root', use_sudo=True)
    sudo('sh /root/unpack.sh {0}'.format(rev))


def push(region_name=Location.EU):
    puppet_revision = revision()
    conn = connect_s3()
    bucket = conn.get_bucket(PUPPET_BUCKET)
    filename = '{0}/pkg/puppet-{1}.tar.gz'.format(dirname(abspath(__file__)), puppet_revision)

    key = Key(bucket)
    key.key = puppet_revision
    key.set_contents_from_filename(filename)
    url =  key.generate_url(300) # give it a 5min window to boot and download the manifests
    return url


@task
@runs_once
def package():
    """
    Package puppet manifests locally.
    """
    with lcd(dirname(abspath(__file__))):
        local('rake package')


@task
def apply():
    """
    Upload, unpack and apply the puppet manifests on the target server(s).
    """
    package()
    unpack()
    local('mkdir -p {0}'.format(logpath(env.start_time)))
    with settings(warn_only=True):
        results = sudo('sh /etc/puppet/apply.sh')
    with open(logpath(env.start_time, env.host_string), 'w') as log:
        log.write(results)


@task
def noop():
    """
    Upload, unpack and apply (with noop) the puppet manifests on the target server(s).
    """
    package()
    unpack()
    local('mkdir -p {0}'.format(logpath(env.start_time)))
    with settings(warn_only=True):
        results = sudo('sh /etc/puppet/noop.sh')
    with open(logpath(env.start_time, env.host_string), 'w') as log:
        log.write(results)


@task
@parallel(2)
def puppetd(action='noop'):
    """
    Control puppetd with the following actions: start, stop, apply, noop.
    """
    with settings(warn_only=True):
        if 'apply' == action:
            agent('apply')
        elif 'stop' == action:
            puppetdstop()
        elif 'start' == action:
            puppetdstart()
        else:
            agent('noop')

@task
@runs_once
def report(start_time=env.start_time):
    """
    Provide a summary report of the puppet run on the remote server.
    """
    resultsfilename = logpath(start_time, 'results')

    if isfile(resultsfilename):
        print(readresults(resultsfilename))
        return

    if len(env.hosts) is 0:
        print('Give a dawg a host yo!')
        return

    local('mkdir -p {0}'.format(logpath(start_time)))
    results = []
    for host in env.hosts:
        result = parsesummary(logpath(start_time, host))
        result['host'] = host
        results.append(result)

    with open(logpath(start_time, 'hosts'), 'w') as hostsfile:
        writehosts(hostsfile, env.hosts)

    with open(resultsfilename, 'w') as resultsfile:
        writeresults(resultsfile, results, start_time)

    print(readresults(resultsfilename))


def writehosts(hostsfile, hosts):
    for host in hosts:
        hostsfile.write('{0}\n'.format(host))


def readresults(resultsfilename):
    if isfile(resultsfilename):
        with open(resultsfilename, 'r') as resultsfile:
            return resultsfile.read()
    else:
        return 'Report not found.'


def writeresults(resultsfile, results, start_time):
    """
    Prints the results of a puppet run at a given point in time.
    """
    template = '%-52s %10s %10s %10s %10s %12s\n'
    title = 'Puppet Run - {0}, Report ID: {1}\n'.format(strftime('%a @ %H:%M (%Y-%m-%d)', gmtime(float(start_time))),
        start_time)
    heading = template % ("Host", "Completed", "Failures", "Noop", "Total", "Duration")
    lines = ""

    for result in results:
        lines += (template % (result.get('host', 'unknown'),
                              result.get('events_success', '-'),
                              result.get('events_failure', '-'),
                              result.get('events_noop', '-'),
                              result.get('events_total', '-'),
                              result.get('time_total', '-')))

    resultsfile.write(title)
    resultsfile.write(heading)
    resultsfile.write(lines)


def filetail(filename, numbytes):
    """
    Opens a file and reads numbytes from the end.
    """
    if isfile(filename) is False:
        return ""
    filestat = stat(filename)
    filesize = filestat[6]
    # this is an arbitrary number that is 2x the size of the puppet summary when I looked at it.
    if filesize < numbytes:
        return ""
    with open(filename, 'r') as logfile:
        logfile.seek(filesize - numbytes) # seek to the last 1000 characters of the file
        return logfile.read()


def parsesummary(filename):
    result = {}
    summary = filetail(filename, 1000).splitlines()[-28:-1]

    # remove any lines that aren't related to the summary (the number of lines is variable)
    while(len(summary)):
        if "Changes:" in summary[0]:
            break
        del summary[0]

    for line in summary:
        section_match = re.match('(\w*):$', line)
        if section_match:
            section = section_match.group(1).lower()
        else:
            matches = re.match('\s*([\w ]*): (.*)$', line)
            key = matches.group(1).lower()
            value = matches.group(2)
            result['{0}_{1}'.format(section, matches.group(1).lower())] = matches.group(2)

    return result



def logpath(start_time, logfilename=''):
    """
    Gives a log path if logfilename is provided as an empty string only provides a directory otherwise terminates the filename with .log

    start_time = float string representing the epoch when the job was started.
    logfilename = file basename
    """
    ext = ''
    if len(logfilename) is not 0:
        ext = '.log'

    return '{0}/results/{1}/{2}{3}'.format(dirname(abspath(__file__)), start_time, logfilename, ext)


def puppetdstop():
    sudo('monit stop puppet-slave')


def puppetdstart():
    sudo('monit start puppet-slave')


def agent(action):
    noop = "--noop" if action == 'noop' else ""
    local('mkdir -p {0}'.format(logpath(env.start_time)))
    with settings(warn_only=True):
        results = sudo("puppetd  --show_diff --color=false --test --summarize {0}".format(noop))
    with open(logpath(env.start_time, env.host_string), 'w') as log:
        log.write(results)
