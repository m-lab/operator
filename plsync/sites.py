#!/usr/bin/python

import pprint
from planetlab.types import *

# NOTE: The legacy network remap is used to re-order the automatically
#   generated, sequential list of ipaddresses to a legacy order to preserve
#   pre-existing slice-and-IP assignments.  Otherwise, slices would be assigned
#   to new IPs, and for now, we wish to preserve the slice-node-ip mapping.
# An appropriate time to remove this and re-assign IPs to slices would be
#   after a major update & reinstallation, such as LXC kernel update.
legacy_network_remap = {
#'SITE' : { HOST_INDEX : 'natural-order-index-list', }
 'ams01': {1: '0,1,2,3,9,7,6,11,5,10,4,6',
           2: '0,1,2,3,9,7,6,11,5,10,4,6',
           3: '4,0,1,2,10,8,6,11,5,7,3,6'},
 'ams02': {1: '7,0,1,8,11,9,6,10,5,6,2,3',
           2: '0,1,2,3,10,7,6,11,8,9,4,5',
           3: '2,3,5,7,8,10,6,11,4,9,1,0'},
 'ath01': {1: '1,0,2,3,8,11,6,10,5,9,4,6',
           2: '0,1,2,3,8,11,6,10,5,9,4,6',
           3: '0,1,2,3,10,11,6,8,5,9,4,6'},
 'ath02': {1: '0,1,2,3,6,11,6,10,5,9,4,7',
           2: '0,1,2,3,6,8,6,11,5,10,4,7',
           3: '11,0,1,2,5,7,6,10,4,9,3,6'},
 'atl01': {1: '11,9,0,7,6,3,6,10,2,8,1,4',
           2: '11,9,0,7,6,3,6,10,2,8,1,4',
           3: '11,9,0,7,6,3,6,10,2,8,1,4'},
 'dfw01': {1: '9,7,6,5,2,8,6,11,4,10,3,1',
           2: '11,9,0,7,6,3,6,10,2,8,1,4',
           3: '11,9,0,7,2,6,6,10,3,5,1,4'},
 'ham01': {1: '0,1,2,3,9,7,6,11,5,10,4,6',
           2: '0,1,2,3,9,7,6,11,5,10,4,6',
           3: '6,5,0,1,9,7,6,11,3,10,2,4'},
 'lax01': {1: '7,10,0,8,6,3,6,11,2,9,1,4',
           2: '2,10,0,8,7,4,6,11,3,9,1,5',
           3: '11,9,0,7,6,3,6,10,2,8,1,4'},
 'lga01': {1: '11,9,0,7,6,3,6,10,2,8,1,4',
           2: '11,9,0,7,6,3,6,10,2,8,1,4',
           3: '4,11,7,9,2,0,6,10,5,8,3,6'},
 'lga02': {1: '11,9,8,7,4,1,6,10,5,6,0,3',
           2: '11,9,0,7,6,3,6,10,2,8,1,4',
           3: '11,9,8,7,5,2,6,10,1,6,0,4'},
 'lhr01': {1: '0,1,2,3,11,10,6,8,5,7,4,6',
           2: '0,1,2,3,9,7,6,11,5,8,4,6',
           3: '0,1,2,3,6,9,6,11,8,10,5,7'},
 'mia01': {1: '11,9,0,7,6,3,6,10,2,8,1,4',
           2: '11,9,0,7,6,3,6,10,2,8,1,4',
           3: '11,9,0,7,6,3,6,10,2,8,1,4'},
 'nuq01': {1: '4,3,11,1,7,5,6,8,2,9,0,10',
           2: '2,3,0,4,6,9,6,5,10,1,11,7',
           3: '2,3,1,4,7,10,6,5,6,0,11,8',
           4: '2,10,5,8,4,3,6,7,6,9,1,11'},
 'ord01': {1: '11,9,0,7,6,3,6,10,2,8,1,4',
           2: '11,9,0,7,6,3,6,10,2,8,1,4',
           3: '11,9,0,7,6,3,6,10,2,8,1,4'},
 'par01': {1: '0,1,2,3,9,7,6,11,5,10,4,6',
           2: '0,1,2,3,9,7,6,11,5,10,4,6',
           3: '5,6,0,1,9,7,6,11,3,10,2,4'},
 'sea01': {1: '11,9,0,7,6,3,6,10,2,8,1,4',
           2: '0,10,1,8,7,4,6,11,3,9,2,5',
           3: '11,9,0,7,6,3,6,10,2,8,1,4'},
 'syd01': {1: '1,2,8,3,0,10,6,11,7,9,4,6',
           2: '2,0,3,5,6,11,6,10,8,9,7,4',
           3: '0,2,4,6,7,1,6,11,9,10,8,5'},
 'wlg01': {1: '0,1,2,3,4,5,6,11,8,10,7,9',
           2: '0,1,2,3,4,5,6,11,8,10,7,9',
           3: '0,1,2,3,4,5,6,11,8,10,7,9'}
}
Network.legacy_network_remap = legacy_network_remap

# name : site prefix, used to generate PL site name, hostnames, etc
# net  : v4 & v6 network prefixes and definitions.

# NOTE: User roles are not managed here.  Visit PlanetLab to change user roles.
user_list = [('Stephen', 'Stuart', 'sstuart@google.com'),
           ('Thomas',  'Gideon', 'gideon@newamerica.net'),
           ('Josh',    'King', 'joshking@newamerica.net'),
           ('Jordan',  'McCarthy', 'mccarthy@opentechinstitute.org'),
           ('Chris',   'Ritzo', 'critzo@opentechinstitute.org'),
           ('Josh',    'Bailey', 'joshb@google.com'),
           ('Tiziana', 'Refice', 'tiziana@google.com')]

site_list = [
    makesite('akl01','163.7.129.0',    '2404:0138:4009::',     'Auckland', 'NZ', -36.850000, 174.783000, user_list, nodegroup='MeasurementLabCentos'),
    makesite('ams01','213.244.128.128','2001:4C08:2003:2::',   'Amsterdam', 'NL', 52.308600, 4.763890, user_list, nodegroup='MeasurementLabCentos'),
    makesite('ams02','72.26.217.64',   '2001:48c8:7::',        'Amsterdam', 'NL', 52.308600, 4.763890, user_list, nodegroup='MeasurementLabCentos'),
    makesite('arn01','213.248.112.64', '2001:2030:0000:001B::','Stockholm', 'SE', 59.651900, 17.918600, user_list, nodegroup='MeasurementLabCentos'),
    makesite('atl01','4.71.254.128',   '2001:1900:3001:C::',   'Atlanta GA', 'US', 33.636700, -84.428100, user_list, nodegroup='MeasurementLabCentos'),
    makesite('ath01','83.212.4.0',     '2001:648:2ffc:2101::', 'Athens', 'GR', 37.936400, 23.944400, user_list, nodegroup='MeasurementLabCentos'),
    makesite('ath02','83.212.5.128',   '2001:648:2ffc:2102::', 'Athens', 'GR', 37.936400, 23.944400, user_list, nodegroup='MeasurementLabCentos'),
    makesite('bog01','186.113.12.0',   '2001:13f8::',          'Bogota', 'CO', 4.583333, -74.066667, user_list, nodegroup='MeasurementLabCentos'),
    makesite('dfw01','38.107.216.0',   '2001:550:2000::',      'Dallas TX', 'US', 32.896900, -97.038100, user_list, nodegroup='MeasurementLabCentos'),
    makesite('dub01','193.1.12.192',   '2001:770:B5::',        'Dublin', 'IE', 53.433300, -6.250000, user_list, nodegroup='MeasurementLabCentos'),
    makesite('ham01','80.239.142.192', '2001:2030:0000:0019::','Hamburg', 'DE', 53.633300, 9.983330, user_list, nodegroup='MeasurementLabCentos'),
    makesite('hnd01','203.178.130.192','2001:200:0:b801::',    'Tokyo', 'JP', 35.552200, 139.780000, user_list, nodegroup='MeasurementLabCentos'),
    makesite('iad01','216.156.197.128','2610:18:111:8001::',   'Washington', 'US', 38.944400, -77.455800, user_list, nodegroup='MeasurementLabCentos'),
    makesite('jnb01','196.24.45.128',  '2001:4200:FFF0:4512::','Johannesburg', 'ZA', -26.203500, 28.133500, user_list, nodegroup='MeasurementLabCentos'),
    makesite('lax01','38.98.51.0',     '2001:550:6800::',      'Los Angeles', 'US', 33.942500, -118.407000, user_list, nodegroup='MeasurementLabCentos'),
    makesite('lba01','109.239.110.0',  '2a00:1a80:1:8::',      'Leeds', 'GB', 53.865800, -1.660560, user_list, nodegroup='MeasurementLabCentos'),
    makesite('lca01','82.116.199.0',   None,                   'Larnaca', 'CY', 34.880900, 33.626000, user_list, exclude=[1,2,3], nodegroup='MeasurementLabCentos'),
    makesite('lga01','74.63.50.0',     '2001:48c8:5:f::',      'New York', 'US', 40.766700, -73.866700, user_list, nodegroup='MeasurementLabCentos'),
    makesite('lga02','38.106.70.128',  '2001:550:1D00:100::',  'New York', 'US', 40.766700, -73.866700, user_list, nodegroup='MeasurementLabCentos'),
    makesite('lhr01','217.163.1.64',   '2001:4C08:2003:3::',   'London', 'UK', 51.469700, -0.451389, user_list, nodegroup='MeasurementLabCentos'),
    makesite('lju01','91.239.96.64',   '2001:67c:27e4:100::',  'Ljubljana', 'SI', 46.223600, 14.457500, user_list, nodegroup='MeasurementLabCentos'),
    makesite('mad01','213.200.103.128','2001:0668:001F:0016::','Madrid', 'ES', 40.466700, -3.566670, user_list, nodegroup='MeasurementLabCentos'),
    makesite('mia01','4.71.210.192',   '2001:1900:3001:A::',   'Miami', 'US', 25.783300, -80.266700, user_list, nodegroup='MeasurementLabCentos'),
    makesite('mil01','213.200.99.192', '2001:0668:001F:0017::','Milan', 'IT', 45.464000, 9.191600, user_list, nodegroup='MeasurementLabCentos'),
    makesite('nbo01','197.136.0.64',   '2C0F:FE08:10:64::',    'Nairobi', 'KE', -1.319170, 36.925800, user_list, nodegroup='MeasurementLabCentos'),
    makesite('nuq01','64.9.225.128',   '2604:ca00:f000::',     'Mountain View', 'US', 37.383300, -122.067000, user_list, count=4, v6gw='2604:ca00:f000::129', nodegroup='MeasurementLabCentos'),
    makesite('nuq02','149.20.5.64',    '2001:4F8:1:1001::',    'Mountain View', 'US', 37.383300, -122.067000, user_list, count=4, nodegroup='MeasurementLabCentos'),
    makesite('ord01','4.71.251.128',   '2001:1900:3001:B::',   'Chicago', 'US', 41.978600, -87.904700, user_list, nodegroup='MeasurementLabCentos'),
    makesite('par01','80.239.168.192', '2001:2030:0000:001A::','Paris', 'FR', 48.858400, 2.349010, user_list, nodegroup='MeasurementLabCentos'),
    makesite('prg01','212.162.51.64',  '2001:4C08:2003:4::',   'Prague', 'CZ', 50.083300, 14.416700, user_list, count=4, nodegroup='MeasurementLabCentos'),
    makesite('sea01','38.102.0.64',    '2001:550:3200:1::',    'Seattle WA', 'US', 47.448900, -122.309000, user_list, nodegroup='MeasurementLabCentos'),
    makesite('svg01','81.167.39.0',    '2a01:798:0:13::',      'Stavanger', 'NO', 58.876700, 5.637780, user_list, nodegroup='MeasurementLabCentos'),
    makesite('syd01','203.5.76.128',   '2001:388:00d0::',      'Sydney', 'AU', -33.946100, 151.177000, user_list, nodegroup='MeasurementLabCentos'),
    makesite('syd02','175.45.79.0',    '2402:7800:0:12::',     'Sydney', 'AU', -33.946100, 151.177000, user_list, nodegroup='MeasurementLabCentos'),
    makesite('tpe01','163.22.28.0',    '2001:e10:6840:28::',   'Taipei', 'TW', 25.077800, 121.224000, user_list, nodegroup='MeasurementLabCentos'),
    makesite('trn01','194.116.85.192', '2001:7F8:23:307::',    'Turin', 'IT', 45.200800, 7.649720, user_list, nodegroup='MeasurementLabCentos'),
    # old ipv6 2c0f:fab0:ffff:1000:: @ tun01
    makesite('tun01','41.231.21.0',    '2001:4350:3000:1::',   'Tunis', 'TN', 36.851600, 10.229100, user_list, nodegroup='MeasurementLabCentos'),
    makesite('vie01','213.208.152.0',  '2a01:190:1700:38::',   'Vienna', 'AT', 48.269000, 16.410700, user_list, nodegroup='MeasurementLabCentos'),
    makesite('wlg01','103.10.233.0',   '2404:2000:3000::',     'Wellington', 'NZ', -41.327200, 174.805000, user_list, nodegroup='MeasurementLabCentos'),

    # Site for M-Lab testing machines
    makesite('nuq0t','64.9.225.192',   '2604:CA00:F000:3::',   None, None, 0,0, user_list, count=4),
   # NOTE: mlc servers need special handling
   #Site(name='mlc',   net=Network(v4='64.9.225.64',     v6='2604:CA00:F000:5::'), domain="measurementlab.net", count=3),
]

