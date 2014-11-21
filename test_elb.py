#!/usr/bin/env python

import unittest
from elb import *
from test_helper import *

class TestElb(unittest.TestCase):
    def test_node_id(self):
        self.assertEqual(node('abc', id='i1234').id, 'i1234')

    def test_node_role(self):
        self.assertEqual(node('abc', role='zulu').tags['Roles'], 'zulu')


if __name__ == '__main__':
    unittest.main()