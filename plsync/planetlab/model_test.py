"""Tests for model."""

import model
import unittest


class TypesTest(unittest.TestCase):

    def setUp(self):
        self.users = [('User', 'Name', 'username@gmail.com')]
        self.sites = [model.makesite(
            'abc01', '192.168.1.0', '2400:1002:4008::', 'Some City', 'US',
            36.850000, 74.783000, self.users, nodegroup='MeasurementLabCentos')]
        self.attrs = [model.Attr('MeasurementLabCentos', disk_max='60000000')]
        # Setup synthetic user, site, and experiment configuration data.
        self.experiments = [
            model.Slice(name='abc_bar', index=1, attrs=self.attrs,
                        users=self.users, use_initscript=True, ipv6='all')]
        # Assign experiments to nodes.
        for hostname, node in self.sites[0]['nodes'].iteritems():
            self.experiments[0].add_node_address(node)

    def test_node_ipv4_and_ipv6(self):
        ipv4s = []
        ipv6s = []
        expected_ipv4s = ['192.168.1.9', '192.168.1.22', '192.168.1.35']
        expected_ipv6s = [
            '2400:1002:4008::9', '2400:1002:4008::22', '2400:1002:4008::35']

        for node in self.sites[0]['nodes'].values():
            ipv4s.append(node.ipv4())
            ipv6s.append(node.ipv6())

        self.assertItemsEqual(expected_ipv4s, ipv4s)
        self.assertItemsEqual(expected_ipv6s, ipv6s)

    def test_slice_ipv4_and_ipv6(self):
        ipv4s = []
        ipv6s = []
        expected_ipv4s = ['192.168.1.11', '192.168.1.24', '192.168.1.37']
        expected_ipv6s = [
            '2400:1002:4008::11', '2400:1002:4008::24', '2400:1002:4008::37']

        for experiment in self.experiments:
            for _, node in experiment['network_list']:
                ipv4s.append(experiment.ipv4(node))
                ipv6s.append(experiment.ipv6(node))

        self.assertItemsEqual(expected_ipv4s, ipv4s)
        self.assertItemsEqual(expected_ipv6s, ipv6s)

    def test_node_hostname(self):
        hostnames = []
        expected_hostnames = [
            'mlab1.abc01.measurement-lab.org',
            'mlab2.abc01.measurement-lab.org',
            'mlab3.abc01.measurement-lab.org'
        ]

        for node in self.sites[0]['nodes'].values():
            hostnames.append(node.hostname())

        self.assertItemsEqual(expected_hostnames, hostnames)

    def test_slice_hostname(self):
        hostnames = []
        expected_hostnames = [
           'bar.abc.mlab1.abc01.measurement-lab.org',
           'bar.abc.mlab2.abc01.measurement-lab.org',
           'bar.abc.mlab3.abc01.measurement-lab.org'
        ]

        for experiment in self.experiments:
            for _, node in experiment['network_list']:
                hostnames.append(experiment.hostname(node))

        self.assertItemsEqual(expected_hostnames, hostnames)


if __name__ == '__main__':
    unittest.main()
