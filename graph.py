from fabric.api import *
from ec2 import running_instances, instances_by_zones, instances_by_role

DEFAULT_REGION = 'eu-west-1'

# TODO: (NF 2013-01-03) Refactor this around a decent data model that is non-AWS specific.

ROLE_TAG='aws:autoscaling:groupName'
ROLE_TAG='category'

def hosts(hosts):
    host_string = ""
    for host in hosts:
        if len(host.private_dns_name) > 0:
            host_string += "    '{0}'[address={1}];\n".format(host.tags.get(ROLE_TAG, 'unknown'), host.private_dns_name)
    return host_string


def network(az, nodes):
    # TODO: (NF 2012-12-10) Remove hardcoded eu-west-1 entry.
    network = """
  network {0} {{
    eu-west-1;
{1}
  }}
"""
    return network.format(az, hosts(nodes))


def groups(roles):
    groups = ""
    colours = ['#9AD7E7', '#B8E3B4', '#FEFFA7', '#FBC3C7', '#DFBEDD']
    i = 0
    for role in roles.keys():
        groups += """
  group {{
    color="{0}";
{1}
  }}
""".format(colours[i % len(colours)], hosts(roles[role]))
        i += 1
    return groups


def nwdiag(zones, roles):
    # TODO: (NF 2012-12-10) Remove hardcoded eu-west-1 entry.
    nwdiag = """
nwdiag {
  eu-west-1 [shape = cloud];
"""
    for zone in zones.keys():
        nwdiag += network(zone, zones[zone])

    nwdiag += groups(roles)

    nwdiag += '}'
    return nwdiag


@task
def region(region=DEFAULT_REGION):
    """
    Graph AWS region into an SVG diagram.
    """
    instances = running_instances(region)
    with open('docs/ec2.diag', 'w') as fd:
        fd.write(nwdiag(instances_by_zones(instances), instances_by_role(instances)))
    try:
        local('nwdiag --ignore-pil -Tsvg docs/ec2.diag')
    except:
        print "Error running nwdiag"

