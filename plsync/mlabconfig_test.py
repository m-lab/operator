"""Tests for mlabconfig."""

import json
import mlabconfig
import mock
import optparse
import os
from planetlab import model
import StringIO
import time
import unittest


class MlabconfigTest(unittest.TestCase):

    def setUp(self):
      self.users = [('User', 'Name', 'username@gmail.com')]
      self.sites = [model.makesite(
          'abc01', '192.168.1.0', '2400:1002:4008::', 'Some City', 'US',
          36.850000, 74.783000, self.users, nodegroup='MeasurementLabCentos')]
      self.attrs = [model.Attr('MeasurementLabCentos', disk_max='60000000')]

    def assertContainsItems(self, results, expected_items):
        """Asserts that every element of expected is present in results."""
        for expected in expected_items:
            self.assertIn(expected, results)

    def test_export_mlab_host_ips(self):
        # Setup synthetic user, site, and experiment configuration data.
        experiments = [model.Slice(name='abc_bar', index=1, attrs=self.attrs,
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

    def test_export_router_and_switch_records(self):
        output = StringIO.StringIO()
        expected_results = [
            mlabconfig.format_a_record('r1.abc01', '192.168.1.1'),
            mlabconfig.format_a_record('s1.abc01', '192.168.1.2'),
        ]

        mlabconfig.export_router_and_switch_records(output, self.sites)

        results = output.getvalue().split('\n')
        self.assertContainsItems(results, expected_results)

    def test_export_pcu_records(self):
        output = StringIO.StringIO()
        expected_results = [
            mlabconfig.format_a_record('mlab1d.abc01', '192.168.1.4'),
            mlabconfig.format_a_record('mlab2d.abc01', '192.168.1.5'),
            mlabconfig.format_a_record('mlab3d.abc01', '192.168.1.6'),
        ]

        mlabconfig.export_pcu_records(output, self.sites)

        results = output.getvalue().split('\n')
        self.assertContainsItems(results, expected_results)

    def test_export_server_records(self):
        output = StringIO.StringIO()
        # This is a subset of expected results.
        expected_results = [
            mlabconfig.format_a_record('mlab1.abc01', '192.168.1.9'),
            mlabconfig.format_a_record('mlab2v4.abc01', '192.168.1.22'),
            mlabconfig.format_aaaa_record('mlab3.abc01', '2400:1002:4008::35'),
            mlabconfig.format_aaaa_record('mlab1v6.abc01', '2400:1002:4008::9')
        ]

        mlabconfig.export_server_records(output, self.sites)

        results = output.getvalue().split('\n')
        self.assertContainsItems(results, expected_results)

    def test_export_experiment_records(self):
        output = StringIO.StringIO()
        experiments = [model.Slice(name='abc_bar', index=1, attrs=self.attrs,
                                   users=self.users, use_initscript=True,
                                   ipv6='all')]
        expected_results = [
            mlabconfig.format_a_record(
                'bar.abc.abc01', '192.168.1.11'),
            mlabconfig.format_a_record(
                'bar.abc.mlab2.abc01', '192.168.1.24'),
            mlabconfig.format_a_record(
                'bar.abcv4.abc01', '192.168.1.11'),
            mlabconfig.format_a_record(
                'bar.abc.mlab2v4.abc01', '192.168.1.24'),
            mlabconfig.format_aaaa_record(
                'bar.abc.abc01', '2400:1002:4008::11'),
            mlabconfig.format_aaaa_record(
                'bar.abc.abc01', '2400:1002:4008::37'),
            mlabconfig.format_aaaa_record(
                'bar.abc.mlab3.abc01', '2400:1002:4008::37'),
            mlabconfig.format_aaaa_record(
                'bar.abcv6.abc01', '2400:1002:4008::11'),
            mlabconfig.format_aaaa_record(
                'bar.abc.mlab1v6.abc01', '2400:1002:4008::11'),
        ]

        mlabconfig.export_experiment_records(output, self.sites, experiments)

        results = output.getvalue().split('\n')
        self.assertContainsItems(results, expected_results)

    @mock.patch.object(mlabconfig, 'get_revision')
    def test_serial_rfc1912(self, mock_get_revision):
        # Fri Oct 31 00:45:00 2015 UTC.
        # 45-minutes should result in 03.
        ts = 1446252300
        mock_get_revision.return_value = '03'

        serial = mlabconfig.serial_rfc1912(time.gmtime(ts))

        self.assertEqual('2015103103', serial)

    @mock.patch.object(os.path, 'exists')
    @mock.patch('__builtin__.open')
    def test_get_revision_when_saved_prefix_is_old_and_revision_is_reset(
        self, mopen, mock_exists):
        prefix = '20151031'
        # All open and disk I/O is mocked out.
        # Pretend the file exists already.
        mock_exists.return_value = True
        # Hold the fake writer so we can check how it was called.
        mock_writer = mock.mock_open()
        # Open is called twice, once to read, and then to write.
        mopen.side_effect = [
            mock.mock_open(
                # Saved prefix is older than current prefix.
                read_data='{"prefix": "20140931", "revision": 1}').return_value,
            mock_writer.return_value
        ]

        s = mlabconfig.get_revision(prefix, '/tmp/fakepath')

        self.assertEqual(s, '00')
        mock_writer.return_value.write.assert_called_once_with(
            '{"prefix": "20151031", "revision": 0}')

    @mock.patch.object(os.path, 'exists')
    @mock.patch('__builtin__.open')
    def test_get_revision_when_file_exists_increments_revision(
        self, mopen, mock_exists):
        prefix = '20151031'
        # All open and disk I/O is mocked out.
        # Pretend the file exists already.
        mock_exists.return_value = True
        # Hold the fake writer so we can check how it was called.
        mock_writer = mock.mock_open()
        # Open is called twice, once to read, and then to write.
        mopen.side_effect = [
            mock.mock_open(
                read_data='{"prefix": "20151031", "revision": 1}').return_value,
            mock_writer.return_value
        ]

        s = mlabconfig.get_revision(prefix, '/tmp/fakepath')

        self.assertEqual(s, '02')
        mock_writer.return_value.write.assert_called_once_with(
            '{"prefix": "20151031", "revision": 2}')

    @mock.patch.object(os.path, 'exists')
    @mock.patch('__builtin__.open')
    def test_get_revision_when_file_is_corrupt_default_values_saved(
        self, mopen, mock_exists):
        prefix = '20151031'
        # All open and disk I/O is mocked out.
        # Pretend the file exists already.
        mock_exists.return_value = True
        # Hold the fake writer so we can check how it was called.
        mock_writer = mock.mock_open()
        # Open is called twice, once to read, and then to write.
        mopen.side_effect = [
            mock.mock_open(
                read_data='THIS IS NOT JSON').return_value,
            mock_writer.return_value
        ]

        s = mlabconfig.get_revision(prefix, '/tmp/fakepath')

        self.assertEqual(s, '00')
        mock_writer.return_value.write.assert_called_once_with(
            '{"prefix": "20151031", "revision": 0}')

    def test_export_mlab_zone_header(self):
        options = optparse.Values()
        options.value = 'middle'
        output = StringIO.StringIO()
        header = StringIO.StringIO('before; %(value)s; after')

        mlabconfig.export_mlab_zone_header(output, header, options)

        self.assertEqual(output.getvalue(), 'before; middle; after')


if __name__ == '__main__':
    unittest.main()
