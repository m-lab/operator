"""Tests for mlabconfig."""

import contextlib
import logging
import mlabconfig
import mock
import optparse
import os
from planetlab import model
import StringIO
import textwrap
import time
import unittest


@contextlib.contextmanager
def OpenStringIO(sio):
    """Creates a StringIO object that is context aware.

    OpenStringIO is useful for testing functions that open and write to a file.

    Example:
        @mock.patch('__builtin__.open')
        def test_some_function(self, mock_open):
            output = StringIO.StringIO()
            mock_open.return_value = OpenStringIO(output)

            some_function()

            self.assertEqual(output.getvalue(), 'Expected content')

    Args:
        sio: StringIO.StringIO, the instance returned by 'open'.
    """
    try:
        yield sio
    finally:
        # Do not close the StringIO object, so testers can access getvalue().
        pass


class BracketTemplateTest(unittest.TestCase):

    def setUp(self):
        self.vars = {'var1': 'Spot', 'var2': 'Dog'}

    def test_substitute_when_template_is_correct(self):
        tmpl = mlabconfig.BracketTemplate('{{var1}} is a {{var2}}')

        actual = tmpl.safe_substitute(self.vars)

        self.assertEqual(actual, 'Spot is a Dog')

    def test_substitute_when_template_is_broken(self):
        tmpl = mlabconfig.BracketTemplate('var1}} is a {{var2')

        actual = tmpl.safe_substitute(self.vars)

        self.assertEqual(actual, 'var1}} is a {{var2')

    def test_substitute_when_template_is_shell(self):
        tmpl1 = mlabconfig.BracketTemplate('$var1 == {{var1}}')
        tmpl2 = mlabconfig.BracketTemplate('${var2} == {{var2}}')

        actual1 = tmpl1.safe_substitute(self.vars)
        actual2 = tmpl2.safe_substitute(self.vars)

        self.assertEqual(actual1, '$var1 == Spot')
        self.assertEqual(actual2, '${var2} == Dog')

    def test_substitute_without_value_returns_unchanged_template(self):
        tmpl = mlabconfig.BracketTemplate('{{evaluated}} {{unevaluated}}')

        actual = tmpl.safe_substitute({'evaluated': 'okay'})

        self.assertEqual(actual, 'okay {{unevaluated}}')


class MlabconfigTest(unittest.TestCase):

    def setUp(self):
        self.users = [('User', 'Name', 'username@gmail.com')]
        self.sites = [model.makesite('abc01',
                                     '192.168.1.0',
                                     '2400:1002:4008::',
                                     'Some City',
                                     'US',
                                     36.850000,
                                     74.783000,
                                     self.users,
                                     nodegroup='MeasurementLabCentos')]
        self.attrs = [model.Attr('MeasurementLabCentos', disk_max='60000000')]
        # Turn off logging output during testing (unless CRITICAL).
        logging.disable(logging.ERROR)

    def assertContainsItems(self, results, expected_items):
        """Asserts that every element of expected is present in results."""
        for expected in expected_items:
            self.assertIn(expected, results)

    def assertDoesNotContainsItems(self, results, unexpected_items):
        """Asserts that every element of unexpected is NOT in results."""
        for unexpected in unexpected_items:
            self.assertNotIn(unexpected, results)

    def test_export_mlab_host_ips(self):
        # Setup synthetic user, site, and experiment configuration data.
        experiments = [model.Slice(name='abc_bar',
                                   index=1,
                                   attrs=self.attrs,
                                   users=self.users,
                                   use_initscript=True,
                                   ipv6='all')]
        # Assign experiments to nodes.
        for node in self.sites[0]['nodes'].values():
            experiments[0].add_node_address(node)
        expected_results = [
            {'hostname': 'mlab1.abc01.measurement-lab.org', 'ipv4': '192.168.1.9', 'ipv6': '2400:1002:4008::9'},
            {'hostname': 'mlab2.abc01.measurement-lab.org', 'ipv4': '192.168.1.22', 'ipv6': '2400:1002:4008::22'},
            {'hostname': 'mlab3.abc01.measurement-lab.org', 'ipv4': '192.168.1.35', 'ipv6': '2400:1002:4008::35'},
            {'hostname': 'bar.abc.mlab1.abc01.measurement-lab.org', 'ipv4': '192.168.1.11', 'ipv6': '2400:1002:4008::11'},
            {'hostname': 'bar.abc.mlab2.abc01.measurement-lab.org', 'ipv4': '192.168.1.24', 'ipv6': '2400:1002:4008::24'},
            {'hostname': 'bar.abc.mlab3.abc01.measurement-lab.org', 'ipv4': '192.168.1.37', 'ipv6': '2400:1002:4008::37'},
        ]

        results = mlabconfig.export_mlab_host_ips(self.sites, experiments)

        self.assertItemsEqual(results, expected_results)

    def test_export_mlab_site_stats(self):
        expected_results = [{"city": "Some City",
                             "metro": ["abc01", "abc"],
                             "country": "US",
                             "site": "abc01",
                             "longitude": 74.783,
                             "latitude": 36.85,
                             "roundrobin": False}]

        sitestats = mlabconfig.export_mlab_site_stats(self.sites)

        self.assertItemsEqual(sitestats, expected_results)

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
        experiments = [model.Slice(name='abc_bar',
                                   index=1,
                                   attrs=self.attrs,
                                   users=self.users,
                                   use_initscript=True,
                                   ipv6='all')]
        expected_results = [
            mlabconfig.format_a_record('bar.abc.abc01', '192.168.1.11'),
            mlabconfig.format_a_record('bar.abc.mlab2.abc01', '192.168.1.24'),
            mlabconfig.format_a_record('bar.abcv4.abc01', '192.168.1.11'),
            mlabconfig.format_a_record('bar.abc.mlab2v4.abc01', '192.168.1.24'),
            mlabconfig.format_aaaa_record('bar.abc.abc01',
                                          '2400:1002:4008::11'),
            mlabconfig.format_aaaa_record('bar.abc.abc01',
                                          '2400:1002:4008::37'),
            mlabconfig.format_aaaa_record('bar.abc.mlab3.abc01',
                                          '2400:1002:4008::37'),
            mlabconfig.format_aaaa_record('bar.abcv6.abc01',
                                          '2400:1002:4008::11'),
            mlabconfig.format_aaaa_record('bar.abc.mlab1v6.abc01',
                                          '2400:1002:4008::11'),
        ]

        mlabconfig.export_experiment_records(output, self.sites, experiments)

        results = output.getvalue().split('\n')
        self.assertContainsItems(results, expected_results)

    def test_export_experiment_records_flattened(self):
        output = StringIO.StringIO()
        experiments = [model.Slice(name='abc_foo',
                                   index=1,
                                   attrs=self.attrs,
                                   users=self.users,
                                   use_initscript=True,
                                   ipv6='all')]
        expected_results = [
            mlabconfig.format_a_record('foo-abc-mlab2-abc01', '192.168.1.24'),
            mlabconfig.format_a_record('foo-abc-mlab2v4-abc01', '192.168.1.24'),
            mlabconfig.format_aaaa_record('foo-abc-mlab3-abc01',
                                          '2400:1002:4008::37'),
            mlabconfig.format_aaaa_record('foo-abc-mlab1v6-abc01',
                                          '2400:1002:4008::11'),
        ]

        unexpected_results = [
            mlabconfig.format_a_record('foo-abc-abc01', '192.168.1.24'),
            mlabconfig.format_a_record('foo-abcv4-abc01', '192.168.1.24'),
            mlabconfig.format_aaaa_record('foo-abc-abc01',
                                          '2400:1002:4008::37'),
            mlabconfig.format_aaaa_record('foo-abcv6-abc01',
                                          '2400:1002:4008::11'),
        ]

        mlabconfig.SSL_EXPERIMENTS = ['abc_foo']
        mlabconfig.export_experiment_records(output, self.sites, experiments)

        results = output.getvalue().split('\n')
        # We are using custom functions here because of the size of the results
        # list. The results list will contain 50+ items. Using the built-in
        # assertItemsEqual() would require creating a very large, unwieldy
        # expected_results list. Using the custom functions allows us to not
        # have to verify the entirety of results, but simply assert that certain
        # key items are in the results. This is likely sufficient because most
        # of the items in results are redundant in form.
        self.assertContainsItems(results, expected_results)
        self.assertDoesNotContainsItems(results, unexpected_results)

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
    def test_get_revision_when_file_exists_increments_revision(self, mopen,
                                                               mock_exists):
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
            mock.mock_open(read_data='THIS IS NOT JSON').return_value,
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

    @mock.patch('__builtin__.open')
    def test_export_mlab_server_network_config(self, mock_open):
        stdout = StringIO.StringIO()
        name_tmpl = '{{hostname}}-foo.ipxe'
        input_tmpl = StringIO.StringIO('ip={{ip}} ; echo ${ip} {{extra}}')
        file_output = StringIO.StringIO()
        mock_open.return_value = OpenStringIO(file_output)

        mlabconfig.export_mlab_server_network_config(
            stdout, self.sites, name_tmpl, input_tmpl, 'mlab1.abc01',
            {'extra': 'value'})

        self.assertEqual(
            file_output.getvalue(), 'ip=192.168.1.9 ; echo ${ip} value')

    @mock.patch('__builtin__.open')
    def test_export_scraper_kubernetes_config(self, mock_open):
        virtual_output_files = {}
        def create_new_fake_file(*args):
            virtual_output_files[args[0]] = StringIO.StringIO()
            return OpenStringIO(virtual_output_files[args[0]])
        mock_open.side_effect = create_new_fake_file
        experiments = [model.Slice(name='abc_foo',
                                   index=1,
                                   attrs=self.attrs,
                                   users=self.users,
                                   use_initscript=True,
                                   rsync_modules=['test1', 'test2'],
                                   ipv6='all')]
        for node in self.sites[0]['nodes'].values():
            experiments[0].add_node_address(node)
        output_template = textwrap.dedent("""\
        host: {{rsync_host}}
        site: {{site_safe}}
        node: {{node_safe}}
        experiment: {{experiment}}
        module: {{rsync_module}}
        """)
        filename_template = ('deployment/{{site_safe}}-{{node_safe}}-'
                             '{{experiment_safe}}-{{rsync_module}}.yml')
        mlabconfig.export_scraper_kubernetes_config(filename_template,
                                                    experiments,
                                                    output_template,
                                                    None)
        expected_output = {
            'deployment/abc01-mlab1-foo-abc-test1.yml': textwrap.dedent("""\
                host: foo.abc.mlab1.abc01.measurement-lab.org
                site: abc01
                node: mlab1
                experiment: foo.abc
                module: test1"""),
            'deployment/abc01-mlab1-foo-abc-test2.yml': textwrap.dedent("""\
                host: foo.abc.mlab1.abc01.measurement-lab.org
                site: abc01
                node: mlab1
                experiment: foo.abc
                module: test2"""),
            'deployment/abc01-mlab2-foo-abc-test1.yml': textwrap.dedent("""\
                host: foo.abc.mlab2.abc01.measurement-lab.org
                site: abc01
                node: mlab2
                experiment: foo.abc
                module: test1"""),
            'deployment/abc01-mlab2-foo-abc-test2.yml': textwrap.dedent("""\
                host: foo.abc.mlab2.abc01.measurement-lab.org
                site: abc01
                node: mlab2
                experiment: foo.abc
                module: test2"""),
            'deployment/abc01-mlab3-foo-abc-test1.yml': textwrap.dedent("""\
                host: foo.abc.mlab3.abc01.measurement-lab.org
                site: abc01
                node: mlab3
                experiment: foo.abc
                module: test1"""),
            'deployment/abc01-mlab3-foo-abc-test2.yml': textwrap.dedent("""\
                host: foo.abc.mlab3.abc01.measurement-lab.org
                site: abc01
                node: mlab3
                experiment: foo.abc
                module: test2""")
        }
        self.assertEqual(set(expected_output.keys()),
                         set(virtual_output_files.keys()))
        for fname, contents in expected_output.items():
            self.assertIn(fname, virtual_output_files)
            self.assertEqual(contents.strip(),
                             virtual_output_files[fname].getvalue().strip())

    @mock.patch('__builtin__.open')
    def test_export_scraper_kubernetes_config_subset(self, mock_open):
        virtual_output_files = {}
        def create_new_fake_file(*args):
            virtual_output_files[args[0]] = StringIO.StringIO()
            return OpenStringIO(virtual_output_files[args[0]])
        mock_open.side_effect = create_new_fake_file
        experiments = [model.Slice(name='abc_foo',
                                   index=1,
                                   attrs=self.attrs,
                                   users=self.users,
                                   use_initscript=True,
                                   rsync_modules=['test1', 'test2'],
                                   ipv6='all')]
        for node in self.sites[0]['nodes'].values():
            experiments[0].add_node_address(node)
        output_template = textwrap.dedent("""\
        machine: {{machine}}
        host: {{rsync_host}}
        site: {{site}}
        node: {{node}}
        experiment: {{experiment}}
        module: {{rsync_module}}
        """)
        filename_template = ('deployment/{{site}}-{{node}}-'
                             '{{experiment_safe}}-{{rsync_module}}.yml')
        mlabconfig.export_scraper_kubernetes_config(filename_template,
                                                    experiments,
                                                    output_template,
                                                    ".*mlab3.*")
        expected_output = {
            'deployment/abc01-mlab3-foo-abc-test1.yml': textwrap.dedent("""\
                machine: mlab3.abc01.measurement-lab.org
                host: foo.abc.mlab3.abc01.measurement-lab.org
                site: abc01
                node: mlab3
                experiment: foo.abc
                module: test1"""),
            'deployment/abc01-mlab3-foo-abc-test2.yml': textwrap.dedent("""\
                machine: mlab3.abc01.measurement-lab.org
                host: foo.abc.mlab3.abc01.measurement-lab.org
                site: abc01
                node: mlab3
                experiment: foo.abc
                module: test2""")
        }
        self.assertEqual(set(expected_output.keys()),
                         set(virtual_output_files.keys()))
        for fname, contents in expected_output.items():
            self.assertIn(fname, virtual_output_files)
            self.assertEqual(contents.strip(),
                             virtual_output_files[fname].getvalue().strip())

    def test_select_prometheus_experiment_targets_includes_all_experiments(
        self):
        # Setup synthetic user, site, and experiment configuration data.
        experiments = [model.Slice(name='abc_bar',
                                   index=1,
                                   attrs=self.attrs,
                                   users=self.users,
                                   use_initscript=True,
                                   ipv6='all')]
        # Assign experiments to nodes.
        for node in self.sites[0]['nodes'].values():
            experiments[0].add_node_address(node)
        expected_targets = [
            {
                'labels': {
                    'experiment': 'bar.abc',
                    'machine': 'mlab2.abc01.measurement-lab.org'
                },
                'targets': [
                    'bar.abc.mlab2.abc01.measurement-lab.org:9090'
                ]
            },
            {
                'labels': {
                    'experiment': 'bar.abc',
                    'machine': 'mlab1.abc01.measurement-lab.org'
                },
                'targets': [
                    'bar.abc.mlab1.abc01.measurement-lab.org:9090'
                ]
            },
            {
                'labels': {
                    'experiment': 'bar.abc',
                    'machine': 'mlab3.abc01.measurement-lab.org'
                },
                'targets': [
                    'bar.abc.mlab3.abc01.measurement-lab.org:9090'
                ]
            }
        ]

        actual_targets = mlabconfig.select_prometheus_experiment_targets(
            experiments, None, ['{{hostname}}:9090'], {}, False, False, '')

        self.assertEqual(len(actual_targets), 3)
        self.assertItemsEqual(expected_targets, actual_targets)

    def test_select_prometheus_experiment_targets_includes_selected(self):
        # Setup synthetic user, site, and experiment configuration data.
        experiments = [model.Slice(name='abc_bar',
                                   index=1,
                                   attrs=self.attrs,
                                   users=self.users,
                                   use_initscript=True,
                                   ipv6='all')]
        # Assign experiments to nodes.
        for node in self.sites[0]['nodes'].values():
            experiments[0].add_node_address(node)
        expected_targets = [
            {
                'labels': {
                    'machine': 'mlab2.abc01.measurement-lab.org',
                    'experiment': 'bar.abc'
                },
                'targets': [
                    'bar.abc.mlab2.abc01.measurement-lab.org:9090'
                ]
            }
        ]

        actual_targets = mlabconfig.select_prometheus_experiment_targets(
            experiments, "bar.abc.mlab2.*", ['{{hostname}}:9090'], {}, False,
            False, '')

        self.assertEqual(len(actual_targets), 1)
        self.assertItemsEqual(expected_targets, actual_targets)

    def test_select_prometheus_experiment_targets_flattens_names(self):
        # Setup synthetic user, site, and experiment configuration data.
        experiments = [model.Slice(name='abc_bar',
                                   index=1,
                                   attrs=self.attrs,
                                   users=self.users,
                                   use_initscript=True,
                                   ipv6='all')]
        # Assign experiments to nodes.
        for node in self.sites[0]['nodes'].values():
            experiments[0].add_node_address(node)
        expected_targets = [
            {
                'labels': {
                    'machine': 'mlab2.abc01.measurement-lab.org',
                    'experiment': 'bar.abc'
                },
                'targets': [
                    'bar-abc-mlab2-abc01.measurement-lab.org:9090'
                ]
            }
        ]

        actual_targets = mlabconfig.select_prometheus_experiment_targets(
            experiments, "bar.abc.mlab2.*", ['{{hostname}}:9090'], {}, False,
            True, '')

        self.assertEqual(len(actual_targets), 1)
        self.assertItemsEqual(expected_targets, actual_targets)

    def test_select_prometheus_experiment_targets_decorated_names(self):
        # Setup synthetic user, site, and experiment configuration data.
        experiments = [model.Slice(name='abc_bar',
                                   index=1,
                                   attrs=self.attrs,
                                   users=self.users,
                                   use_initscript=True,
                                   ipv6='all')]
        # Assign experiments to nodes.
        for node in self.sites[0]['nodes'].values():
            experiments[0].add_node_address(node)
        expected_targets = [
            {
                'labels': {
                    'machine': 'mlab2.abc01.measurement-lab.org',
                    'experiment': 'bar.abc'
                },
                'targets': [
                    'bar.abc.mlab2v4.abc01.measurement-lab.org:9090'
                ]
            }
        ]

        actual_targets = mlabconfig.select_prometheus_experiment_targets(
            experiments, "bar.abc.mlab2.*", ['{{hostname}}:9090'], {}, False,
            False, 'v4')

        self.assertEqual(len(actual_targets), 1)
        self.assertItemsEqual(expected_targets, actual_targets)

    def test_select_prometheus_node_targets(self):
        expected_targets = [
            {
                'labels': {
                    'machine': 'mlab2.abc01.measurement-lab.org'
                },
                'targets': [
                    'mlab2.abc01.measurement-lab.org:9090'
                ]
            }
        ]

        actual_targets = mlabconfig.select_prometheus_node_targets(
            self.sites, "mlab2.*", ['{{hostname}}:9090'], {}, '')

        self.assertEqual(len(actual_targets), 1)
        self.assertItemsEqual(actual_targets, expected_targets)

    def test_select_prometheus_node_targets_decorated_names(self):
        expected_targets = [
            {
                'labels': {
                    'machine': 'mlab2.abc01.measurement-lab.org'
                },
                'targets': [
                    'mlab2v6.abc01.measurement-lab.org:9090'
                ]
            }
        ]

        actual_targets = mlabconfig.select_prometheus_node_targets(
            self.sites, "mlab2.*", ['{{hostname}}:9090'], {}, 'v6')

        self.assertEqual(len(actual_targets), 1)
        self.assertItemsEqual(actual_targets, expected_targets)

    def test_select_prometheus_node_mulitple_targets(self):
        expected_targets = [
            {
                'labels': {
                    'machine': 'mlab2.abc01.measurement-lab.org'
                },
                'targets': [
                    'mlab2.abc01.measurement-lab.org:9090',
                    'mlab2.abc01.measurement-lab.org:8080'
                ]
            }
        ]

        actual_targets = mlabconfig.select_prometheus_node_targets(
            self.sites, "mlab2.*", ['{{hostname}}:9090', '{{hostname}}:8080'],
            {}, '')

        self.assertEqual(len(actual_targets), 1)
        self.assertItemsEqual(actual_targets, expected_targets)

    def test_select_prometheus_site_targets(self):
        expected_targets = [
            {
                'labels': {
                    'site': 'abc01'
                },
                'targets': [
                    's1.abc01.measurement-lab.org:9116'
                ]
            }
        ]

        actual_targets = mlabconfig.select_prometheus_site_targets(
            self.sites, None, ['s1.{{sitename}}.measurement-lab.org:9116'], {})

        self.assertEqual(len(actual_targets), 1)
        self.assertItemsEqual(actual_targets, expected_targets)


if __name__ == '__main__':
    unittest.main()
