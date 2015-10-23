"""Tests for mlabconfig."""

import mlabconfig
import StringIO
import unittest
from planetlab import types
import json


class MlabconfigTest(unittest.TestCase):

    def setUp(self):
      self.users = [('User', 'Name', 'username@gmail.com')]
      self.sites = [types.makesite(
          'abc01', '192.168.1.0', '2400:1002:4008::', 'Some City', 'US',
          36.850000, 74.783000, self.users, nodegroup='MeasurementLabCentos')]
      self.attrs = [types.Attr('MeasurementLabCentos', disk_max='60000000')]

    def assertContainsItems(self, results, expected_items):
        """Asserts that every element of expected is present in results."""
        for expected in expected_items:
            self.assertIn(expected, results)

    def test_export_mlab_host_ips(self):
        # Setup synthetic user, site, and experiment configuration data.
        experiments = [types.Slice(name='abc_bar', index=1, attrs=self.attrs,
                                   users=self.users, use_initscript=True,
                                   ipv6='all')]
        # Assign experiments to nodes.
        for hostname, node in self.sites[0]['nodes'].iteritems():
            experiments[0].add_node_address(node)
        output = StringIO.StringIO()
        expected_results = [
            'mlab1.abc01.measurement-lab.org,192.168.1.9,2400:1002:4008::9',
            'mlab2.abc01.measurement-lab.org,192.168.1.22,2400:1002:4008::22',
            'mlab3.abc01.measurement-lab.org,192.168.1.35,2400:1002:4008::35',
            ('bar.abc.mlab1.abc01.measurement-lab.org,192.168.1.11,'
             '2400:1002:4008::11'),
            ('bar.abc.mlab2.abc01.measurement-lab.org,192.168.1.24,'
             '2400:1002:4008::24'),
            ('bar.abc.mlab3.abc01.measurement-lab.org,192.168.1.37,'
             '2400:1002:4008::37'),
        ]

        mlabconfig.export_mlab_host_ips(output, self.sites, experiments)

        results = output.getvalue().split()
        self.assertItemsEqual(results, expected_results)

    def test_export_mlab_site_stats(self):
        output = StringIO.StringIO()
        expected_results = [{"city": "Some City", "metro": ["abc01", "abc"],
                             "country": "US", "site": "abc01",
                             "longitude": 74.783, "latitude": 36.85}]

        mlabconfig.export_mlab_site_stats(output, self.sites)

        results = json.loads(output.getvalue())
        self.assertItemsEqual(results, expected_results)


if __name__ == '__main__':
    unittest.main()
