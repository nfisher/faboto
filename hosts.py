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
    env.gateway = 'bastion.eu-west-1.i.lve.hailocab.net'

@task
@runs_once
def viaus():
    env.gateway = 'bastion.us-east-1.i.lve.hailocab.net'

@task
@runs_once
def euhms():
    """
    HOST: EU HMS
    """
    env.gateway = 'bastion.eu-west-1.i.lve.hailocab.net'
    execute('ec2.running', 'h2o-hms.h2o-hms-loadbalancer-lve')


@task
@runs_once
def eujstat():
    """
    HOST: EU Jstats
    """
    env.gateway = 'bastion.eu-west-1.i.lve.hailocab.net'
    execute('ec2.running', 'jstatsapp')

@task
@runs_once
def usjstat():
    """
    HOST: US Jstats
    """
    env.gateway = 'bastion.us-east-1.i.lve.hailocab.net'
    execute('ec2.running', 'jstatsapp', 'us-east-1')
