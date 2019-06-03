#!/usr/bin/python

import json
import ipinfo
import optparse
import sites
import time

physical = """local sitesDefault = import 'sites/_default.jsonnet';

sitesDefault {
  name: '%(name)s',
  annotations+: {
    type: 'physical',
  },
  network+: {
    ipv4+: {
      prefix: '%(v4)s',
    },
    ipv6+: {
      prefix: %(v6)s,
    },
  },
  transit+: {
    provider: '%(provider)s',
    uplink: '%(uplink)s',
    asn: '%(asn)s',
  },
  location+: {
    continent_code: '%(continent)s',
    country_code: '%(country)s',
    metro: '%(metro)s',
    city: '%(city)s',
    state: '%(state)s',
    latitude: %(latitude)s,
    longitude: %(longitude)s,
  },
  lifecycle+: {
    created: '2019-01-01',
  },
}
"""

cloud = """local sitesDefault = import 'sites/_default.jsonnet';

sitesDefault {
  name: '%(name)s',
  annotations+: {
    type: 'cloud',
  },
  machines+: {
    count: 1,
  },
  network+: {
    ipv4+: {
      prefix: '%(v4)s/32',
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
    metro: '%(metro)s',
    city: '%(city)s',
    state: '%(state)s',
    latitude: %(latitude)s,
    longitude: %(longitude)s,
  },
  lifecycle+: {
    created: '2018-01-01',
  },
}
"""

GeoIP_country_continent = [
    "--", "AS", "EU", "EU", "AS", "AS", "NA", "NA", "EU", "AS", "NA", "AF",
    "AN", "SA", "OC", "EU", "OC", "NA", "AS", "EU", "NA", "AS", "EU", "AF",
    "EU", "AS", "AF", "AF", "NA", "AS", "SA", "SA", "NA", "AS", "AN", "AF",
    "EU", "NA", "NA", "AS", "AF", "AF", "AF", "EU", "AF", "OC", "SA", "AF",
    "AS", "SA", "NA", "NA", "AF", "AS", "AS", "EU", "EU", "AF", "EU", "NA",
    "NA", "AF", "SA", "EU", "AF", "AF", "AF", "EU", "AF", "EU", "OC", "SA",
    "OC", "EU", "EU", "NA", "AF", "EU", "NA", "AS", "SA", "AF", "EU", "NA",
    "AF", "AF", "NA", "AF", "EU", "AN", "NA", "OC", "AF", "SA", "AS", "AN",
    "NA", "EU", "NA", "EU", "AS", "EU", "AS", "AS", "AS", "AS", "AS", "EU",
    "EU", "NA", "AS", "AS", "AF", "AS", "AS", "OC", "AF", "NA", "AS", "AS",
    "AS", "NA", "AS", "AS", "AS", "NA", "EU", "AS", "AF", "AF", "EU", "EU",
    "EU", "AF", "AF", "EU", "EU", "AF", "OC", "EU", "AF", "AS", "AS", "AS",
    "OC", "NA", "AF", "NA", "EU", "AF", "AS", "AF", "NA", "AS", "AF", "AF",
    "OC", "AF", "OC", "AF", "NA", "EU", "EU", "AS", "OC", "OC", "OC", "AS",
    "NA", "SA", "OC", "OC", "AS", "AS", "EU", "NA", "OC", "NA", "AS", "EU",
    "OC", "SA", "AS", "AF", "EU", "EU", "AF", "AS", "OC", "AF", "AF", "EU",
    "AS", "AF", "EU", "EU", "EU", "AF", "EU", "AF", "AF", "SA", "AF", "NA",
    "AS", "AF", "NA", "AF", "AN", "AF", "AS", "AS", "OC", "AS", "AF", "OC",
    "AS", "EU", "NA", "OC", "AS", "AF", "EU", "AF", "OC", "NA", "SA", "AS",
    "EU", "NA", "SA", "NA", "NA", "AS", "OC", "OC", "OC", "AS", "AF", "EU",
    "AF", "AF", "EU", "AF", "--", "--", "--", "EU", "EU", "EU", "EU", "NA",
    "NA", "NA", "AF", "--"]

GeoIP_country_code = [
    "--", "AP", "EU", "AD", "AE", "AF", "AG", "AI", "AL", "AM", "CW", "AO",
    "AQ", "AR", "AS", "AT", "AU", "AW", "AZ", "BA", "BB", "BD", "BE", "BF",
    "BG", "BH", "BI", "BJ", "BM", "BN", "BO", "BR", "BS", "BT", "BV", "BW",
    "BY", "BZ", "CA", "CC", "CD", "CF", "CG", "CH", "CI", "CK", "CL", "CM",
    "CN", "CO", "CR", "CU", "CV", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM",
    "DO", "DZ", "EC", "EE", "EG", "EH", "ER", "ES", "ET", "FI", "FJ", "FK",
    "FM", "FO", "FR", "SX", "GA", "GB", "GD", "GE", "GF", "GH", "GI", "GL",
    "GM", "GN", "GP", "GQ", "GR", "GS", "GT", "GU", "GW", "GY", "HK", "HM",
    "HN", "HR", "HT", "HU", "ID", "IE", "IL", "IN", "IO", "IQ", "IR", "IS",
    "IT", "JM", "JO", "JP", "KE", "KG", "KH", "KI", "KM", "KN", "KP", "KR",
    "KW", "KY", "KZ", "LA", "LB", "LC", "LI", "LK", "LR", "LS", "LT", "LU",
    "LV", "LY", "MA", "MC", "MD", "MG", "MH", "MK", "ML", "MM", "MN", "MO",
    "MP", "MQ", "MR", "MS", "MT", "MU", "MV", "MW", "MX", "MY", "MZ", "NA",
    "NC", "NE", "NF", "NG", "NI", "NL", "NO", "NP", "NR", "NU", "NZ", "OM",
    "PA", "PE", "PF", "PG", "PH", "PK", "PL", "PM", "PN", "PR", "PS", "PT",
    "PW", "PY", "QA", "RE", "RO", "RU", "RW", "SA", "SB", "SC", "SD", "SE",
    "SG", "SH", "SI", "SJ", "SK", "SL", "SM", "SN", "SO", "SR", "ST", "SV",
    "SY", "SZ", "TC", "TD", "TF", "TG", "TH", "TJ", "TK", "TM", "TN", "TO",
    "TL", "TR", "TT", "TV", "TW", "TZ", "UA", "UG", "UM", "US", "UY", "UZ",
    "VA", "VC", "VE", "VG", "VI", "VN", "VU", "WF", "WS", "YE", "YT", "RS",
    "ZA", "ZM", "ME", "ZW", "A1", "A2", "O1", "AX", "GG", "IM", "JE", "BL",
    "MF", "BQ", "SS", "O1"]

continent = dict(zip(GeoIP_country_code, GeoIP_country_continent))

sitestats = []
sitestats.append({
    'site': 'chs0c',
    'metro': ['chs', 'chs0c'],
    'city': 'Charleston_SC',
    'country': 'US',
    'latitude': 32.896663,
    'longitude': -80.039184,
    'roundrobin': False,
    'v4': '35.237.214.243'
})
sitestats.append({
    'site': 'iad0c',
    'metro': ['iad', 'iad0c'],
    'city': 'Washington_DC',
    'country': 'US',
    'latitude': 38.944400,
    'longitude': -77.455800,
    'roundrobin': False,
    'v4': '35.236.226.12',
})
sitestats.append({
    'site': 'lax0c',
    'metro': ['lax', 'lax0c'],
    'city': 'Los Angeles_CA',
    'country': 'US',
    'latitude': 33.942500,
    'longitude': -118.407200,
    'roundrobin': False,
    'v4': '35.235.125.164',
})
sitestats.append({
    'site': 'oma0c',
    'metro': ['oma', 'oma0c'],
    'city': 'Omaha_NE',
    'country': 'US',
    'latitude': 41.303760,
    'longitude': -95.893282,
    'roundrobin': False,
    'v4': '35.226.110.109',
})
sitestats.append({
    'site': 'pdx0c',
    'metro': ['pdx', 'pdx0c'],
    'city': 'Portland_OR',
    'country': 'US',
    'latitude': 45.589191,
    'longitude': -122.600228,
    'roundrobin': False,
    'v4': '35.230.97.78',
})
sitestats.append({
    'site': 'tyo01',
    'metro': ['tyo', 'tyo01'],
    'city': 'Tokyo',
    'country': 'JP',
    'latitude': 35.552200,
    'longitude': 139.780000,
    'roundrobin': False,
    'v4': '35.200.102.226',
})
sitestats.append({
    'site': 'tyo02',
    'metro': ['tyo', 'tyo02'],
    'city': 'Tokyo',
    'country': 'JP',
    'latitude': 35.552200,
    'longitude': 139.780000,
    'roundrobin': False,
    'v4': '35.200.34.149',
})
sitestats.append({
    'site': 'tyo03',
    'metro': ['tyo', 'tyo03'],
    'city': 'Tokyo',
    'country': 'JP',
    'latitude': 35.552200,
    'longitude': 139.780000,
    'roundrobin': False,
    'v4': '35.200.112.17',
})


def generate_physical(sitelist, switch, outdir):
    """Generates jsonnet files for sites in given sitelist.

    Given sites should be physical machines. Each site is annotated with
    uplink information from given switch configuration data.

    As well, each site is annotated with ASN data from ipinfo.io.
    """
    info = ipinfo.getHandler()
    for site in sitelist:
        v = {}
        lat = site['location']['latitude']
        lon = site['location']['longitude']
        country = site['location']['country']
        v4 = site['net']['v4']['prefix']
        if site['net']['v6']:
            v6 = site['net']['v6']['prefix']
        else:
            v6 = None
        city_raw = site['location']['city']
        if '_' in city_raw:
            city, state = city_raw.split('_')
        else:
            city = city_raw
            state = ''

        d = info.getDetails(v4)
        if d.org:
            asn, provider = d.org.split(' ', 1)
        else:
            asn = 'AS-unknown'
            provider = 'unknown'

        v['name'] = site['name']
        v['latitude'] = lat
        v['longitude'] = lon
        v['metro'] = site['name'][0:3]
        v['city'] = city
        v['state'] = state
        v['country'] = country
        v['continent'] = continent[country]
        v['provider'] = provider
        if v['name'] not in switch:
            print 'skipping', v['name']
            continue
        v['uplink'] = switch[v['name']]['uplink_speed']
        v['asn'] = asn
        v['v4'] = v4 + '/26'
        v['v6'] = '\'' + v6 + '/64\'' if v6 else 'null'

        s = physical % v
        print v['name']
        with open('%s/%s.jsonnet' % (outdir, v['name']), 'w') as output:
            output.write(s)
        time.sleep(.2)


def generate_cloud(sitelist, outdir):
    """Generates jsonnet files for sites in given sitelist."""
    for site in sitelist:
        v = {}
        lat = site['latitude']
        lon = site['longitude']
        v4 = site['v4']
        v6 = 'null'
        city_raw = site['city']
        if '_' in city_raw:
            city, state = city_raw.split('_')
        else:
            city = city_raw
            state = ''

        v['name'] = site['site']
        v['latitude'] = lat
        v['longitude'] = lon
        v['metro'] = site['site'][0:3]
        v['city'] = city
        v['state'] = state

        v['v4'] = v4
        v['v6'] = v6

        s = cloud % v
        print v['name']
        with open('%s/%s.jsonnet' % (outdir, v['name']), 'w') as output:
            output.write(s)
        time.sleep(.2)


def usage():
    return """
DESCRIPTION:
    convert.py generates JSONNET files for physical and cloud sites from the
    current sites & cloud configuration.

EXAMPLES:
    ./convert.py --outdir $PWD/sites --switch switch-details.json
"""


def parse_flags():
    parser = optparse.OptionParser(usage=usage())
    parser.add_option(
        '',
        '--switch',
        metavar='switch-details.json',
        dest='switch',
        default='switch-details.json',
        help='The full path to switch details JSON file.')
    parser.add_option(
        '',
        '--outdir',
        dest='outdir',
        default='sites',
        help='Write output files to given directory name.')
    return parser.parse_args()


def main():
    options, _ = parse_flags()
    switch = json.loads(open(options.switch).read())
    generate_physical(sites.site_list, switch, options.outdir)
    #generate_cloud(sitestats, options.outdir)


if __name__ == '__main__':
    main()
