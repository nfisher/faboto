from fabric.api import *
from boto import ec2
from boto.ec2 import elb
from itertools import chain, product
from time import sleep

# TODO: (NF 2012-12-14) Push this into a config.yaml or similar.
DEFAULT_REGION = 'eu-west-1'

@task
def ls(elb_name=None, region=DEFAULT_REGION):
    """
    Print ec2 nodes grouped by elb.
    """
    elbconn = elb.connect_to_region(region)
    lbs = sorted(elbconn.get_all_load_balancers(elb_name), key=lambda elb: elb.name)

    ec2conn = ec2.connect_to_region(region)
    # TODO: (NF 2013-01-20) Should probably consider filtering by instance id when an elb_name is provided to the task.
    reservations = ec2conn.get_all_instances(filters={'instance-state-name': 'running'})
    instances = list(chain.from_iterable(map(lambda r: r.instances, reservations)))
    elb_health = None

    if elb_name is not None:
      elb_health = elbconn.describe_instance_health(elb_name)

    for lb in lbs:
        print("\n%-55s %-50s" % (lb.name, lb.dns_name))
        for lb_instance, instance in product(lb.instances, instances):
            if instance.id == lb_instance.id:
                name = instance.tags.get('Name', 'unknown')
                instance_health = '-'
                if elb_health is not None:
                  instance_health = filter(lambda h: h.instance_id == instance.id, elb_health)[0].state
                print('  %-12s %-12s %-40s %-50s %-10s' % (instance.id, instance_health, name, instance.public_dns_name, instance.placement))

@task
def rm(elb_name, *instance_ids):
    """
    Remove the specified instance ids' from the named elb.

    Example:

    fab elb.rm:$ELB_NAME,i-12345                     # Removes a single instance from the load balancer
    fab elb.rm:$ELB_NAME,i-12345,i-23456,i-34567     # Removes 3 instances from the load balancer

    """
    elbconn = elb.connect_to_region(DEFAULT_REGION)
    elbconn.deregister_instances(elb_name, instance_ids)
    
    state = None
    for i in range(1, 10):
        state = elbconn.describe_instance_health(elb_name, instance_ids)[0].state
        if state == "OutOfService":
            return
        sleep(2 * i)

    abort("The instance {0} was not properly removed from the load balancer".format(instance_ids))


@task
def add(elb_name, *instance_ids):
    """
    Add the specified instance ids' to the named elb.

    Example:

    fab elb.add:$ELB_NAME,i-12345                     # Adds a single instance to the load balancer
    fab elb.add:$ELB_NAME,i-12345,i-23456,i-34567     # Adds 3 instances to the load balancer

    """
    elbconn = elb.connect_to_region(DEFAULT_REGION)
    elbconn.register_instances(elb_name, instance_ids)

    state = None
    for i in range(1, 10):
        # TODO: (NF 2013-03-05) Should verify each instance rather than just one.
        state = elbconn.describe_instance_health(elb_name, instance_ids)[0].state
        if state == "InService":
            print("{2} is {0} after {1} attempt(s)".format(state, i, instance_ids))
            return
        sleep(2 * i)

    abort("The instance {0} was not properly added to the load balancer [{1}]".format(instance_ids, state))
