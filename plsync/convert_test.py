"""Tests for convert."""

import convert
import ipinfo
import mock
import tempfile
import textwrap
import unittest

class ConvertTest(unittest.TestCase):

    @mock.patch.object(ipinfo, 'getHandler')
    def test_generate_physical(self, mock_gethandler):
        class d:
            org = 'AS1234 Foo ISP'
            country = 'GH'
        mock_gethandler.return_value.getDetails.return_value = d
        switch = {
            "acc02": {
                "auto_negotiation": "yes",
                "community": "fake12345678",
                "flow_control": "no",
                "switch_make": "hp",
                "uplink_port": "24",
                "uplink_speed": "1g"
            },
        }
        sites = [
            {
                'name': 'acc02',
                'location': {
                    'latitude': 5.6060,
                    'longitude': -0.1681,
                    'city': 'Accra',
                },
                'net': {
                    'v4': {
                        'prefix': '196.49.14.192',
                    },
                    'v6': {
                        'prefix': None,
                    }
                }
            }
        ]

        outdir = tempfile.mkdtemp()
        convert.generate_physical(sites, switch, outdir)

        actual = open(outdir + '/acc02.jsonnet').read()
        expected = textwrap.dedent("""\
            local sitesDefault = import 'sites/_default.jsonnet';

            sitesDefault {
              name: 'acc02',
              annotations+: {
                type: 'physical',
              },
              network+: {
                ipv4+: {
                  prefix: '196.49.14.192/26',
                },
                ipv6+: {
                  prefix: null,
                },
              },
              transit+: {
                provider: 'Foo ISP',
                uplink: '1g',
                asn: 'AS1234',
              },
              location+: {
                continent_code: 'AF',
                country_code: 'GH',
                metro: 'acc',
                city: 'Accra',
                state: '',
                latitude: 5.606,
                longitude: -0.1681,
              },
              lifecycle+: {
                created: '2019-01-01',
              },
            }
            """)
        self.assertEqual(actual, expected)

    def test_generate_cloud(self):
        sites = [
            {
                'site': 'tyo03',
                'metro': ['tyo', 'tyo03'],
                'city': 'Tokyo',
                'country': 'JP',
                'latitude': 35,
                'longitude': 139,
                'roundrobin': False,
                'v4': '35.200.112.17',
            }
        ]

        outdir = tempfile.mkdtemp()
        convert.generate_cloud(sites, outdir)

        actual = open(outdir + '/tyo03.jsonnet').read()
        expected = textwrap.dedent("""\
            local sitesDefault = import 'sites/_default.jsonnet';

            sitesDefault {
              name: 'tyo03',
              annotations+: {
                type: 'cloud',
              },
              machines+: {
                count: 1,
              },
              network+: {
                ipv4+: {
                  prefix: '35.200.112.17/32',
                },
                ipv6+: {
                  prefix: null,
                },
              },
              transit+: {
                provider: 'Google',
                uplink: '1g',
              },
              location+: {
                continent_code: 'NA',
                country_code: 'US',
                metro: 'tyo',
                city: 'Tokyo',
                state: '',
                latitude: 35,
                longitude: 139,
              },
              lifecycle+: {
                created: '2018-01-01',
              },
            }
            """)
        self.assertEqual(actual, expected)
