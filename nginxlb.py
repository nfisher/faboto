from fabric.api import *
import ec2
import elb
from puppet import agent

DEFAULT_REGION = 'eu-west-1'

@task
def nodes():
    execute('ec2.running', 'nginx-lb')

@task
def deploy():
    """
    Pulls nodes out of balance, deploys puppet, verifies a list of urls, restores node into balance.
    """
    env.user = 'deploy'
    execute('nginxlb.nodes')
    execute('nginxlb.rundeploy')
    execute('puppet.report')

@task
def rundeploy():
    role_name = 'nginx-lb'
    current_hostname = env.host_string
    instances = ec2.running_instances(DEFAULT_REGION, role_name)
    instance = next(instance for instance in instances if instance.public_dns_name == current_hostname)
    elb.rm(role_name, instance.id)
    agent('apply')
    runverify()
    elb.add(role_name, instance.id)

@task
def verify():
    execute('nginxlb.nodes')
    execute('nginxlb.runverify')

@task
def runverify():
    # TODO: (NF 2013-02-13) Should probably validate with a string found in the content.
    urls = [{'host': 'www.hailoapp.com', 'request_uri': '/'} 
        ]
    for url in urls:
        local('curl -f -I --retry 3 -H "Host: {0}" --max-redirs 0 -L http://{1}{2}'.format(
            url['host'],
            env.host_string,
            url['request_uri']))
