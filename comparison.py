from fabric.api import *
from boto import ec2
from boto.ec2 import elb

DEFAULT_REGION = 'eu-west-1'

@task
def deploy():
    """
    Deploy the comparison service to all the nodes with the comparison role
    """
    execute("ec2.running", "comparison13")
    execute('comparison.rundeploy')


@task
def rundeploy(region=DEFAULT_REGION, elb_name="energy-comparison"):
    """
    Deploy the comparison service to a single node
    """
    role = "comparison13"
    current_hostname = env.host_string
    instances = ec2.running_instances(region, role)
    instance = next(instance for instance in instances if instance.public_dns_name == current_hostname)
    elb.rm(elb_name, instance.id)
    local("cd ../energy-comparison && bundle exec cap {0} deploy".format(instance.tags.get('Name', '')))
    verify(current_hostname)
    elb.add(elb_name, instance.id)


@task
def verify(current_hostname):
    """
    Verify the energy comparison service is working correctly on all the nodes
    """
    # TODO: (NF 2012-12-13) Switch to python library for greater flexibility.
    env.results[env.host_string] = local(
        'curl -f -I --retry 20 http://apiconsumer:greenhall@{0}/v1/suppliers'.format(
            current_hostname))