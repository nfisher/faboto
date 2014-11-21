from os import stat, getenv
from os.path import dirname, abspath, isfile
from fabric.api import *

import comparison
import ec2
import elb
import glob
import graph
import hosts
import iam
import nginxlb
import puppet
import re
import s3


env.skip_bad_hosts = True
env.connection_attempts = 3
env.timeout = 3
env.shell = '/bin/sh -c'
if isfile('{0}/.ssh/config'.format(getenv('HOME'))):
    env.use_ssh_config = True
env.results = {}
env.linewise = True
env.keepalive = 10

@task
def listeningports():
    """
    Print the listening ports and their associated processes.
    """
    sudo('netstat -ltunp')


@task
@runs_once
def printhosts():
    """
    Print the current list of hosts.
    """
    print('Host List:')
    for host in env.hosts:
        print(host)
    print("Total Hosts: {0}".format(len(env.hosts)))

@task
@parallel
def hostname():
    """
    Print the hostname.
    """
    run("hostname")

@task
def psaux():
    """
    Print the current running processes.
    """
    run("hostname")
    run("ps aux")
    

@task
@parallel(5)
def aptreset():
    sudo('killall apt-get;rm -rf /var/lib/apt/lists/partial/*')
