"""Tests for mlabconfig."""

import contextlib
import logging
import mlabconfig
import mock
from planetlab import model
import StringIO
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

sites = [
   {
      "name": "abc01",
      "annotations": {
         "type": "physical"
      },
      "location": {
         "city": "Some City",
         "continent_code": "NA",
         "country_code": "US",
         "latitude": 36.850000,
         "longitude": 74.783000,
         "metro": "abc",
         "state": ""
      },
      "machines": {
         "count": 4,
         "disk": "sda",
         "iface": "eth0"
      },

      "network": {
         "ipv4": {
            "dns1": "8.8.8.8",
            "dns2": "8.8.4.4",
            "prefix": "192.168.1.0/26",
         },
         "ipv6": {
            "dns1": "2001:4860:4860::8888",
            "dns2": "2001:4860:4860::8844",
            "prefix": "2400:1002:4008::/64",
         }
      },
      "nodes": [
         {
            "experiments": [
               {
                  "cloud_enabled": True,
                  "flat_hostname": True,
                  "hostname": "bar.abc.mlab1.abc01.measurement-lab.org",
                  "index": 2,
                  "ipv6_enabled": True,
                  "name": "bar.abc",
                  "v4": {
                     "ip": "163.7.129.11"
                  },
                  "v6": {
                     "ip": "2404:138:4009::11"
                  }
               },
            ],
            "hostname": "mlab1.abc01.measurement-lab.org",
            "index": 1,
            "v4": {
               "broadcast": "192.168.1.63",
               "dns1": "8.8.8.8",
               "dns2": "8.8.4.4",
               "gateway": "192.168.1.1",
               "ip": "192.168.1.9",
               "netmask": "255.255.255.192",
               "network": "192.168.1.0/26",
               "subnet": 26
            },
            "v6": {
               "dns1": "2001:4860:4860::8888",
               "dns2": "2001:4860:4860::8844",
               "gateway": "2400:1002:4008::1",
               "ip": "2400:1002:4008::9",
               "network": "2400:1002:4008::/64",
               "subnet": 64
            }
         },
      ]
   },
]

class MlabconfigTest(unittest.TestCase):

    def setUp(self):
        self.users = [('User', 'Name', 'username@gmail.com')]
        self.sites = sites
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

    @mock.patch('__builtin__.open')
    def test_export_mlab_server_network_config(self, mock_open):
        stdout = StringIO.StringIO()
        name_tmpl = '{{hostname}}-foo.ipxe'
        input_tmpl = StringIO.StringIO('ip={{ipv4_address}} ; echo ${ip} {{extra}}')
        file_output = StringIO.StringIO()
        mock_open.return_value = OpenStringIO(file_output)

        mlabconfig.export_mlab_server_network_config(
            stdout, self.sites, name_tmpl, input_tmpl, 'mlab1.abc01',
            {'extra': 'value'}, False)

        self.assertEqual(
            file_output.getvalue(), 'ip=192.168.1.9 ; echo ${ip} value')

    def test_select_prometheus_experiment_targets_includes_all_experiments(
        self):
        expected_targets = [
            {
                'labels': {
                    'experiment': 'bar.abc',
                    'machine': 'mlab1.abc01.measurement-lab.org'
                },
                'targets': [
                    'bar.abc.mlab1.abc01.measurement-lab.org:9090'
                ]
            },
        ]

        actual_targets = mlabconfig.select_prometheus_experiment_targets(
            self.sites, None, ['{{hostname}}:9090'], {}, False, False, '',
            False)

        self.assertEqual(len(actual_targets), 1)
        self.assertItemsEqual(expected_targets, actual_targets)

    def test_select_prometheus_experiment_targets_includes_selected(self):
        expected_targets = [
            {
                'labels': {
                    'machine': 'mlab1.abc01.measurement-lab.org',
                    'experiment': 'bar.abc'
                },
                'targets': [
                    'bar.abc.mlab1.abc01.measurement-lab.org:9090'
                ]
            }
        ]

        actual_targets = mlabconfig.select_prometheus_experiment_targets(
            self.sites, "bar.abc.mlab1.*", ['{{hostname}}:9090'], {},
            False, False, '', False)

        self.assertEqual(len(actual_targets), 1)
        self.assertItemsEqual(expected_targets, actual_targets)

    def test_select_prometheus_experiment_targets_flattens_names(self):
        expected_targets = [
            {
                'labels': {
                    'machine': 'mlab1.abc01.measurement-lab.org',
                    'experiment': 'bar.abc'
                },
                'targets': [
                    'bar-abc-mlab1-abc01.measurement-lab.org:9090'
                ]
            }
        ]

        actual_targets = mlabconfig.select_prometheus_experiment_targets(
            self.sites, "bar.abc.mlab1.*", ['{{hostname}}:9090'], {},
            False, True, '', False)

        self.assertEqual(len(actual_targets), 1)
        self.assertItemsEqual(expected_targets, actual_targets)

    def test_select_prometheus_experiment_targets_decorated_names(self):
        expected_targets = [
            {
                'labels': {
                    'machine': 'mlab1.abc01.measurement-lab.org',
                    'experiment': 'bar.abc'
                },
                'targets': [
                    'bar.abc.mlab1v4.abc01.measurement-lab.org:9090'
                ]
            }
        ]

        actual_targets = mlabconfig.select_prometheus_experiment_targets(
            self.sites, "bar.abc.mlab1.*", ['{{hostname}}:9090'], {}, False,
            False, 'v4', False)

        self.assertEqual(len(actual_targets), 1)
        self.assertItemsEqual(expected_targets, actual_targets)

    def test_select_prometheus_node_targets(self):
        expected_targets = [
            {
                'labels': {
                    'machine': 'mlab1.abc01.measurement-lab.org'
                },
                'targets': [
                    'mlab1.abc01.measurement-lab.org:9090'
                ]
            }
        ]

        actual_targets = mlabconfig.select_prometheus_node_targets(
            self.sites, "mlab1.*", ['{{hostname}}:9090'], {}, '', False)

        self.assertEqual(len(actual_targets), 1)
        self.assertItemsEqual(actual_targets, expected_targets)

    def test_select_prometheus_node_targets_decorated_names(self):
        expected_targets = [
            {
                'labels': {
                    'machine': 'mlab1.abc01.measurement-lab.org'
                },
                'targets': [
                    'mlab1v6.abc01.measurement-lab.org:9090'
                ]
            }
        ]

        actual_targets = mlabconfig.select_prometheus_node_targets(
            self.sites, "mlab1.*", ['{{hostname}}:9090'], {}, 'v6', False)

        self.assertEqual(len(actual_targets), 1)
        self.assertItemsEqual(actual_targets, expected_targets)

    def test_select_prometheus_node_mulitple_targets(self):
        expected_targets = [
            {
                'labels': {
                    'machine': 'mlab1.abc01.measurement-lab.org'
                },
                'targets': [
                    'mlab1.abc01.measurement-lab.org:9090',
                    'mlab1.abc01.measurement-lab.org:8080'
                ]
            }
        ]

        actual_targets = mlabconfig.select_prometheus_node_targets(
            self.sites, "mlab1.*", ['{{hostname}}:9090', '{{hostname}}:8080'],
            {}, '', False)

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
            self.sites, None, ['s1.{{sitename}}.measurement-lab.org:9116'], {},
            False)

        self.assertEqual(len(actual_targets), 1)
        self.assertItemsEqual(actual_targets, expected_targets)


if __name__ == '__main__':
    unittest.main()
