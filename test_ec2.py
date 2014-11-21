#!/usr/bin/env python

import unittest
from ec2 import *
from test_helper import *

class TestEc2(unittest.TestCase):
    def test_node_placement(self):
        self.assertEqual(node('abc').placement, 'eu-west-1a')


    def test_node_role(self):
        self.assertEqual(node('abc', role='zulu').tags['Roles'], 'zulu')


    def test_instances_by_zone(self):
        hosts = [
            node('anode01', zone='eu-west-1a'),
            node('bnode01', zone='eu-west-1b'),
            node('anode02', zone='eu-west-1a'),
            node('anode03', zone='eu-west-1a')
        ]
        expected = {'eu-west-1a': [hosts[0], hosts[2], hosts[3]], 'eu-west-1b': [hosts[1]]}
        self.assertEqual(instances_by_zones(hosts), expected)

    def test_instances_by_role(self):
        hosts = [
            node('anode01', role='web193', zone='eu-west-1a'),
            node('bnode01', role='apps', zone='eu-west-1b'),
            node('cnode01', role='aux', zone='eu-west-1c'),
            node('bnode02', role='apps', zone='eu-west-1a')
        ]
        expected = {'web193': [hosts[0]], 'apps': [hosts[1], hosts[3]], 'aux': [hosts[2]]}
        self.assertEqual(instances_by_role(hosts), expected)

    def test_exclude_instances(self):
        expected = [ 'anode02' ]
        hosts = [ 'anode01', 'anode02' ] 
        instances = [node('anode01', role='web193', zone='eu-west-1a')]
        self.assertEqual(exclude_instances(hosts, instances), expected)

    def test_bootstrap_data_contains_role(self):
        user_data = bootstrap_data('nginxlb','http://s3.com/puppet.tgz').splitlines()
        self.assertEqual("ROLE=nginxlb", user_data[1])

    def test_bootstrap_data_contains_puppet_url(self):
        user_data = bootstrap_data('nginxlb','http://s3.com/puppet.tgz').splitlines()
        self.assertEqual("PUPPET_URL='http://s3.com/puppet.tgz'", user_data[2])

if __name__ == '__main__':
    unittest.main()
