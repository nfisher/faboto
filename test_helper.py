class struct():
    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def node(name, dns=None, role='web', zone='eu-west-1a', id='i1234'):
    if dns is None:
        dns = name
    return struct(public_dns_name=dns, placement=zone, tags={'Roles': role, 'Name': name}, id=id)


def elb(name, instances):
    return struct(name=name, instances=instances)


