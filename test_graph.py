#!/usr/bin/env python

import unittest
from graph import *
from test_helper import *


# TODO: (NF 2012-12-07) These tests are stupid fragile and need a good refactoring.
class TestGraph(unittest.TestCase):
    def test_diagram(self):
        expected = """
nwdiag {
  eu-west-1 [shape = cloud];

  network eu-west-1b {
    eu-west-1;
    'web02'[address=web02];

  }

  network eu-west-1c {
    eu-west-1;
    'web03'[address=web03];

  }

  network eu-west-1a {
    eu-west-1;
    'web01'[address=web01];

  }

  group {
    color="#9AD7E7";
    'web01'[address=web01];
    'web02'[address=web02];
    'web03'[address=web03];

  }
}"""
        zones = {'eu-west-1a': [node('web01')], 'eu-west-1b': [node('web02')], 'eu-west-1c': [node('web03')]}
        roles = {'web': [node('web01'), node('web02'), node('web03')]}
        self.assertEqual(nwdiag(zones, roles), expected)


    def test_hosts(self):
        expects = "    'web'[address=web01];\n"
        webhosts = [node('web', 'web01')]
        self.assertEqual(hosts(webhosts), expects)


    def test_empty_network(self):
        expects = """
  network eu-west-1a {
    eu-west-1;

  }
"""
        self.assertEqual(network('eu-west-1a', []), expects)


    def test_groups(self):
        expects = """
  group {
    color="#9AD7E7";
    'web'[address=web01];

  }
"""
        hosts = [node('web', 'web01')]
        self.assertEqual(groups({'web': hosts}), expects)


    def test_single_host_network(self):
        expects = """
  network eu-west-1b {
    eu-west-1;
    'web'[address=web01];

  }
"""
        hosts = [node('web', 'web01')]
        self.assertEqual(network('eu-west-1b', hosts), expects)


if __name__ == '__main__':
    unittest.main()
