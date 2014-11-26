from fabric.api import *

@task
@runs_once
def vagrant(user='vagrant'):
    """
    HOST: Local vagrant host configuration.
    """
    env.user = user
    env.port = local('vagrant ssh-config|grep Port|cut -d\' \' -f 4', capture=True)
    env.key_filename = local('vagrant ssh-config|grep IdentityFile|cut -d\' \' -f 4', capture=True)
    env.hosts = ['127.0.0.1']

@task
@runs_once
def viaeu():
    """
    Route hosts via EU gateway.
    """
    gateway = 'bastion.eu-west-1.i.lve.hailocab.net'
    if env.gateway is None:
        env.gateway = gateway
    elif env.gateway is not gateway:
        abort("cannot mix regions want US bastion but currently is {}.".format(env.gateway))


@task
@runs_once
def viaus():
    """
    Route hosts via US gateway.
    """
    gateway = 'bastion.us-east-1.i.lve.hailocab.net'
    if env.gateway is None:
        env.gateway = gateway
    elif env.gateway is not gateway:
        abort("cannot mix regions want US bastion but currently is {}.".format(env.gateway))


@task
@runs_once
def euhms():
    """
    HOST: EU HMS
    """
    execute('hosts.viaeu')
    execute('ec2.running', 'h2o-hms.h2o-hms-loadbalancer-lve')


@task
@runs_once
def eujstat():
    """
    HOST: EU Jstats
    """
    execute('hosts.viaeu')
    execute('ec2.running', 'jstatsapp')

@task
@runs_once
def usjstat():
    """
    HOST: US Jstats
    """
    execute('hosts.viaus')
    execute('ec2.running', 'jstatsapp', 'us-east-1')


@task
@runs_once
def eunsq():
    """
    HOST: EU NSQ pprof
    """
    execute('hosts.viaus')
    execute('ec2.running', 'nsq-general.nsq-general-global01-live')

@task
@runs_once
def usnsq():
    """
    HOST: US NSQ pprof
    """
    execute('hosts.viaus')
    execute('ec2.running', 'nsq-general.nsq-general-global01-live', 'us-east-1')
