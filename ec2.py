from fabric.api import abort, env, execute, prompt, runs_once, task
from datetime import datetime
from boto import ec2, exception
from itertools import chain, groupby
from os import getenv
from os.path import dirname, abspath, isfile
from puppet import push

# TODO: (NF 2012-12-14) Push this into a config.yaml or similar.
DEFAULT_REGION = 'eu-west-1'
DEFAULT_INSTANCE_TYPE = 'c1.medium'
# Keep updated with the amd64 precise instance-store AMI for eu-west-1 from http://cloud-images.ubuntu.com/locator/ec2/
EU_PRECISE_AMI = 'ami-1a070f6e'


GROUP_TAG='aws:autoscaling:groupName'
ROLE_TAG='category'

def running_instances(region_name, role_name=None):
    """Retrieve all running instances.

    Keyword arguments:
    region_name -- AWS region to retrieve the running instances from.
    role_name -- filter using only nodes with a 'Roles' tag that matches role_name.

    """
    if role_name is '':
        role_name = None

    filters = {'instance-state-name': 'running'}
    if role_name is not None:
        if "." in role_name:
            role_name, group_name = role_name.split('.')
            if role_name == '':
                filters = {'tag:'+GROUP_TAG: group_name, 'instance-state-name': 'running'}
            else:
                filters = {'tag:'+ROLE_TAG: role_name,'tag:'+GROUP_TAG: group_name, 'instance-state-name': 'running'}
        else:
            filters = {'tag:'+ROLE_TAG: role_name, 'instance-state-name': 'running'}
    ec2conn = ec2.connect_to_region(region_name)
    reservations = ec2conn.get_all_instances(filters=filters)
    instances = list(chain.from_iterable(map(lambda r: r.instances, reservations)))
    return instances


def instances_by_zones(instances):
    """Group instances by AZ's.

    Keyword arguments:
    instances -- boto.Instances list.

    """
    # Collection needs to be sorted before being fed to groupby.
    sorted_instances = sorted(instances, cmp=lambda x, y: cmp(x.placement, y.placement))
    return dict((key, list(group)) for key, group in groupby(sorted_instances, key=lambda i: i.placement))


def composite_tag(tags):
    return tags.get(ROLE_TAG, '') + "." + tags.get(GROUP_TAG, '')

def instances_by_role(instances):
    """Group instances by the tag 'Roles'.

    Keyword arguments:
    instances -- boto.Instances list.
    """
    # Collection needs to be sorted before being fed to groupby.
    sorted_instances = sorted(instances,
            cmp=lambda x, y: cmp(composite_tag(x.tags), composite_tag(y.tags)))
    return dict(
        (key, list(group)) for key, group in groupby(sorted_instances, key=lambda i: composite_tag(i.tags)))


def create_boto_config():
    key = prompt("What is your AWS_ACCESS_KEY_ID?")
    secret = prompt("What is your AWS_SECRET_ACCESS_KEY?")
    with open('{0}/.boto'.format(getenv('HOME')), 'w') as botoconfig:
        template = """
[Credentials]
aws_access_key_id = {0}
aws_secret_access_key = {1}
""".strip()
        botoconfig.write(template.format(key, secret))


def bootstrap_data(role, puppet_url=None):
    """

    Keyword arguments:
    role - The role to bootstrap this instance with.
    puppet_url - the url to download a puppet tarball from.
    """
    try:
        with open('{0}/puppet/bootstrap_precise.sh'.format(dirname(abspath(__file__))), 'r') as fd:
            lines = fd.read().splitlines()
            lines.insert(1, u'ROLE={0}'.format(role))
            lines.insert(2, u'PUPPET_URL=\'{0}\''.format(puppet_url))
            user_data = '\n'.join(lines)
    except IOError as e:
        abort(e.message)
    return user_data

@task
def firstapply():
    """
    Freshly minted hosts require this to run puppet against them.
    """
    env.user = 'ubuntu'
    env.port = 22
    execute('puppet.apply')
    execute('puppet.report')

@task
def config(region_name=DEFAULT_REGION):
    """Prompt user for their AWS access and secret key.

    Keyword arguments:
    region_name -- upload id_rsa.pub key for use in this region (default DEFAULT_REGION).

    """
    try:
        with open('{0}/.boto'.format(getenv('HOME'))) as f: pass
    except IOError as e:
        create_boto_config()

    try:
        with open('{0}/.ssh/id_rsa.pub'.format(getenv('HOME'))) as f:
            user = getenv('USER')
            conn = ec2.connect_to_region(region_name)
            conn.import_key_pair(user, f.read())
            print('Uploaded key as {0}'.format(user))
    except IOError:
        print('Unable to read id_rsa key.')
    except exception.EC2ResponseError as ec2ex:
        print(ec2ex.error_message)


@task
def agentapply(role_name):
    """Puppet agent will sync with the master and apply changes for the specified role.

    Keyword arguments:
    role_name -- filter using only nodes with a 'Roles' tag that matches role_name.

    """
    env.port = 8008
    env.user = 'deploy'
    execute('ec2.running', role_name)
    execute('puppet.puppetd', 'apply')
    execute('puppet.report')


@task
def localapply(role_name):
    """Puppet will apply changes without a master against the specified role.

    Keyword arguments:
    role_name -- filter using only nodes with a 'Roles' tag that matches role_name.

    """
    execute('ec2.running', role_name)
    execute('puppet.apply')
    execute('puppet.report')


@task
def rm(*instance_ids):
    """Destroy the list of ec2 instances.

    Keyword arguments:
    instance_ids -- list of EC2 instance id's to destroy.

    Example usage:

    fab ec2.rm:i1234        # Destroy 1 instance (i1234).
    fab ec2.rm:i1234,i5678  # Destroy 2 instances (i1234, i5678).

    """
    answer = prompt(
        "You're about to delete a node. You've got to ask yourself one question; Do I feel lucky? Well, do ya, punk? (y/n)").rstrip().lower()
    if(answer == 'y'):
        ec2conn = ec2.connect_to_region(DEFAULT_REGION)
        ec2conn.terminate_instances(instance_ids=instance_ids)


def launch_instances(ec2conn, image_id, instance_type, key_name, region_name, security_groups, user_data,
                     zonecounts):
    instance_ids = []
    for suffix in zonecounts:
        zonecount = zonecounts[suffix]
        placement = region_name + suffix
        if zonecount > 0:
            print('Creating {0} instance(s) in {1}.'.format(zonecount, placement))
            reservation = ec2conn.run_instances(image_id=image_id, placement=placement, min_count=zonecount,
                max_count=zonecount, instance_type=instance_type,
                security_groups=security_groups, user_data=user_data,
                key_name=key_name)
            for instance in reservation.instances:
                instance_ids.append(instance.id)

    return instance_ids


def tag_instances(ec2conn, instance_ids, role_name):
    name = role_name + datetime.now().strftime('-%Y%m%d-%H%M')
    ec2conn.create_tags(instance_ids, {'Name': name, 'Roles': role_name})


@task
def add(role_name, azonecount=0, bzonecount=0, czonecount=0, dzonecount=0, ezonecount=0, instance_type=DEFAULT_INSTANCE_TYPE,
        region_name=DEFAULT_REGION, image_id=EU_PRECISE_AMI):
    """Launch the defined role with the specified number of servers in the AZ's.

    Keyword arguments:
    role_name -- EC2 'Roles' tag to apply to the instances being spawned.
    azonecount -- Number of instances to spawn in Zone A (default 0)
    bzonecount -- Number of instances to spawn in Zone B (default 0)
    czonecount -- Number of instances to spawn in Zone C (default 0)
    dzonecount -- Number of instances to spawn in Zone D (default 0)
    ezonecount -- Number of instances to spawn in Zone E (default 0)
    instance_type -- EC2 instance type (default 'm1.medium')
    region_name -- AWS region to launch instance (default 'eu-west-1')
    image_id -- AMI image to launch.

    Example Usage:

    fab ec2.add:web193,1,1,1  # Create 1 instance in Zones A, B, and C with the role web193.
    fab ec2.add:web193,1      # Create 1 instance in Zone A.

    """
    zonecounts = {'a': int(azonecount), 'b': int(bzonecount), 'c': int(czonecount), 'd': int(dzonecount),
                  'e': int(ezonecount)}
    if (sum(zonecounts.values()) == 0):
      abort('You must specify a number of nodes to provision.')

    execute('puppet.package')

    conn = ec2.connect_to_region(region_name)
    # TODO: (NF 2012-12-12) may want to use placement zone lookup.
    # TODO: (NF 2013-02-04) Not really keen on this security group definition living here.
    security_groups = ['internal']
    # TODO: (NF 2013-01-29) Consider using a default for key_name.
    key_name = getenv('USER')

    # upload puppet manifests to S3
    puppet_url = push()

    user_data = bootstrap_data(role_name, puppet_url)
    instance_ids = launch_instances(conn, image_id, instance_type, key_name, region_name, security_groups, user_data,
        zonecounts)
    tag_instances(conn, instance_ids, role_name)

    return instance_ids


@task
def ls(role_name=None, region_name=DEFAULT_REGION):
    """Print running hosts ordered by role.

    Keyword arguments:
    role_name -- EC2 'Roles' tag to apply to the instances being spawned, None will disable the filter (default None).
    region_name -- AWS region to retrieve the running instances from (default 'eu-west-1')

    Example Usage:

    fab ec2.ls          # List all hosts ordered by role.
    fab ec2.ls:web193   # List all hosts belonging to the web193 role.

    """
    instances = instances_by_role(running_instances(region_name, role_name=role_name))
    for role_name in sorted(instances.keys()):
        print(role_name)
        for instance in instances[role_name]:
            name = instance.tags.get('Name', '')
            print('  %-11s %-11s %-14s %-12s %-30s %-50s' % (
                instance.id, instance.instance_type, instance.vpc_id, instance.placement, name, instance.private_ip_address))


@task
@runs_once
def exclude(*role_names):
    """HOST: Remove the hosts of the specified role from the hosts list.

    Keyword arguments:
    role_names -- role(s) of nodes to exclude from the hosts list.

    Example Usage:

    fab ec2.running ec2.exclude:metrics printhosts  # print all of the hosts except metrics

    """
    region_name = DEFAULT_REGION
    for role_name in role_names:
        env.hosts = exclude_instances(env.hosts, running_instances(region_name, role_name))


def exclude_instances(hosts, excluded_instances):
    excluded_hostnames = [h.public_dns_name for h in excluded_instances]
    return filter(lambda h: h not in excluded_hostnames, hosts)


@task(alias='run')
@runs_once
def running(role_name=None, region_name=DEFAULT_REGION):
    """HOST: Append all of the ec2 instances to the hosts list.

    Keyword arguments:
    role_names -- role(s) of nodes to include in the hosts list.
    region_name -- AWS region to retrieve the running instances from (default 'eu-west-1')

    Example Usage:

    fab ec2.run printhosts               # print all running hosts
    fab ec2.running:nginx-lb printhosts  # print all nginx nodes
    fab ec2.running:cassandra printhosts # print all cassandra nodes

    """
    instances = instances_by_zones(running_instances(region_name, role_name))
    zones = instances.keys()

    # find the maximum length for a given AZ partition
    max_len = 0
    for zone in zones:
        current_len = len(instances[zone])
        if current_len > max_len:
            max_len = current_len

    # this is a naive way to ensure parallel tasks will be spread across zones
    for i in range(0, max_len):
        for zone in zones:
            zoneinstances = instances[zone]
            if i < len(zoneinstances):
                instance = zoneinstances[i]
                env.hosts.append(instance.private_ip_address)
