#!/usr/bin/python

import pprint
from planetlab.model import *
from users import user_list

# NOTE: The legacy network remap is used to re-order the automatically
#   generated, sequential list of ipaddresses to a legacy order to preserve
#   pre-existing slice-and-IP assignments.  Otherwise, slices would be assigned
#   to new IPs, and for now, we wish to preserve the slice-node-ip mapping.
# An appropriate time to remove this and re-assign IPs to slices would be
#   after a major update & reinstallation, such as LXC kernel update.
legacy_network_remap = {
#'SITE' : { HOST_INDEX : 'natural-order-index-list', }
 'ams01': {1: '0,1,2,3,9,7,8,11,5,10,4,6',
           2: '0,1,2,3,9,7,8,11,5,10,4,6',
           3: '4,0,1,2,10,8,9,11,5,7,3,6'},
 'ams02': {1: '7,0,1,8,11,9,4,10,5,6,2,3',
           2: '0,1,2,3,10,7,6,11,8,9,4,5',
           3: '2,3,5,7,8,10,6,11,4,9,1,0'},
 'atl01': {1: '11,9,0,7,6,3,5,10,2,8,1,4',
           2: '11,9,0,7,6,3,5,10,2,8,1,4',
           3: '11,9,0,7,6,3,5,10,2,8,1,4'},
 'dfw01': {1: '9,7,6,5,2,8,0,11,4,10,3,1',
           2: '11,9,0,7,6,3,5,10,2,8,1,4',
           3: '11,9,0,7,2,6,8,10,3,5,1,4'},
 'ham01': {1: '0,1,2,3,9,7,8,11,5,10,4,6',
           2: '0,1,2,3,9,7,8,11,5,10,4,6',
           3: '6,5,0,1,9,7,8,11,3,10,2,4'},
 'lax01': {1: '7,10,0,8,6,3,5,11,2,9,1,4',
           2: '2,10,0,8,7,4,6,11,3,9,1,5',
           3: '11,9,0,7,6,3,5,10,2,8,1,4'},
 'lga02': {1: '11,9,8,7,4,1,2,10,5,6,0,3',
           2: '11,9,0,7,6,3,5,10,2,8,1,4',
           3: '11,9,8,7,5,2,3,10,1,6,0,4'},
 'lhr01': {1: '0,1,2,3,11,10,9,8,5,7,4,6',
           2: '0,1,2,3,9,7,10,11,5,8,4,6',
           3: '0,1,2,3,6,9,4,11,8,10,5,7'},
 'mia01': {1: '11,9,0,7,6,3,5,10,2,8,1,4',
           2: '11,9,0,7,6,3,5,10,2,8,1,4',
           3: '11,9,0,7,6,3,5,10,2,8,1,4'},
 'ord01': {1: '11,9,0,7,6,3,5,10,2,8,1,4',
           2: '11,9,0,7,6,3,5,10,2,8,1,4',
           3: '11,9,0,7,6,3,5,10,2,8,1,4'},
 'par01': {1: '0,1,2,3,9,7,8,11,5,10,4,6',
           2: '0,1,2,3,9,7,8,11,5,10,4,6',
           3: '5,6,0,1,9,7,8,11,3,10,2,4'},
 'sea01': {1: '11,9,0,7,6,3,5,10,2,8,1,4',
           2: '0,10,1,8,7,4,6,11,3,9,2,5',
           3: '11,9,0,7,6,3,5,10,2,8,1,4'},
 'syd01': {1: '1,2,8,3,0,10,5,11,7,9,4,6',
           2: '2,0,3,5,6,11,1,10,8,9,7,4',
           3: '0,2,4,6,7,1,3,11,9,10,8,5'}
}
Network.legacy_network_remap = legacy_network_remap

# name : site prefix, used to generate PL site name, hostnames, etc
# net  : v4 & v6 network prefixes and definitions.

# The "arch" parameter of makesite() is a facility that PLC uses to pass the
# correct kernel arguments when booting nodes at a given site. Currently defined
# "arch" values are:
#
# i386 - none
# x86_64 - "noapic acpi=off"
# x86_64-r420 - "pci=nobios acpi=off"
# x86_64-r630 - none

site_list = [
    makesite('acc02','196.49.14.192',  None,                   'Accra', 'GH', 5.6060, -0.1681, user_list, exclude=[1,2,3], arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('akl01','163.7.129.0',    '2404:138:4009::',      'Auckland', 'NZ', -36.850000, 174.783000, user_list, nodegroup='MeasurementLabCentos'),
    makesite('ams01','213.244.128.128','2001:4c08:2003:2::',   'Amsterdam', 'NL', 52.308600, 4.763890, user_list, nodegroup='MeasurementLabCentos'),
    makesite('ams02','72.26.217.64',   '2001:48c8:7::',        'Amsterdam', 'NL', 52.308600, 4.763890, user_list, nodegroup='MeasurementLabCentos'),
    makesite('arn01','213.248.112.64', '2001:2030:0:1b::',     'Stockholm', 'SE', 59.651900, 17.918600, user_list, nodegroup='MeasurementLabCentos'),
    makesite('atl01','4.71.254.128',   '2001:1900:3001:c::',   'Atlanta_GA', 'US', 33.636700, -84.428100, user_list, nodegroup='MeasurementLabCentos'),
    makesite('atl02','38.112.151.64',  '2001:550:5b00:1::',    'Atlanta_GA', 'US', 33.636700, -84.428100, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('atl03','64.86.200.192',  '2001:5a0:3b02::',      'Atlanta_GA', 'US', 33.636700, -84.428100, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('atl04','173.205.0.192',  '2001:668:1f:1c::',     'Atlanta_GA', 'US', 33.636700, -84.428100, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('atl05','67.106.215.192', '2610:18:111:c002::',   'Atlanta_GA', 'US', 33.636700, -84.428100, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('atl06','70.42.177.64',   '2600:c0b:2002:5::',    'Atlanta_GA', 'US', 33.636700, -84.428100, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos'),
    makesite('ath03','193.201.166.128', '2001:648:25e0::',     'Athens', 'GR', 37.936400, 23.944400, user_list, count=4, v6gw='2001:648:25e0::129', nodegroup='MeasurementLabCentos'),
    makesite('beg01','188.120.127.0',  '2001:7f8:1e:6::',      'Belgrade', 'RS', 44.821600, 20.292100, user_list, nodegroup='MeasurementLabCentos'),
    makesite('bkk01','61.7.252.0',     '2001:c38:9041::',      'Bangkok', 'TH', 13.690400, 100.750100, user_list, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('bog01','190.15.11.0',    None,                   'Bogota', 'CO', 4.5833, -74.066700, user_list, exclude=[1,2,3], nodegroup='MeasurementLabCentos'),
    makesite('den01','184.105.23.64',  '2001:470:1:250::',     'Denver_CO', 'US', 39.856100, -104.673700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos'),
    makesite('den02','4.34.58.0',      '2001:1900:2200:49::',  'Denver_CO', 'US', 39.856100, -104.673700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos'),
    makesite('den03','65.46.46.128',   '2610:18:10e:8003::',   'Denver_CO', 'US', 39.856100, -104.673700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos'),
    makesite('den04','128.177.109.64', '2001:438:fffd:2c::',   'Denver_CO', 'US', 39.856100, -104.673700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos'),
    makesite('dfw01','38.107.216.0',   '2001:550:2000::',      'Dallas_TX', 'US', 32.896900, -97.038100, user_list, nodegroup='MeasurementLabCentos'),
    makesite('dfw02','64.86.132.64',   '2001:5a0:3f00::',      'Dallas_TX', 'US', 32.896900, -97.038100, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('dfw03','4.15.35.128',    '2001:1900:2200:44::',  'Dallas_TX', 'US', 32.896900, -97.038100, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('dfw04','208.177.76.64',  '2610:18:10e:2::',      'Dallas_TX', 'US', 32.896900, -97.038100, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('dfw05','128.177.163.64', '2001:438:fffd:30::',   'Dallas_TX', 'US', 32.896900, -97.038100, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('dfw06','63.251.44.192',  '2600:c12:1002:4::',    'Dallas_TX', 'US', 32.896900, -97.038100, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos'),
    makesite('dub01','193.1.12.192',   '2001:770:b5::',        'Dublin', 'IE', 53.433300, -6.250000, user_list, nodegroup='MeasurementLabCentos'),
    makesite('ham01','80.239.142.192', '2001:2030:0:19::',     'Hamburg', 'DE', 53.633300, 9.983330, user_list, nodegroup='MeasurementLabCentos'),
    makesite('hnd01','203.178.130.192','2001:200:0:b801::',    'Tokyo', 'JP', 35.552200, 139.780000, user_list, nodegroup='MeasurementLabCentos'),
    makesite('iad01','216.156.197.128','2610:18:111:8001::',   'Washington_DC', 'US', 38.944400, -77.455800, user_list, nodegroup='MeasurementLabCentos'),
    makesite('iad02','38.90.140.128',  '2001:550:200:7::',     'Washington_DC', 'US', 38.944400, -77.455800, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('iad03','66.198.10.128',  '2001:5a0:3c03::',      'Washington_DC', 'US', 38.944400, -77.455800, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('iad04','173.205.4.0',    '2001:668:1f:21::',     'Washington_DC', 'US', 38.944400, -77.455800, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('iad05','4.35.238.192',   '2001:1900:2200:46::',  'Washington_DC', 'US', 38.944400, -77.455800, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('jnb01','196.24.45.128',  '2001:4200:fff0:4512::','Johannesburg', 'ZA', -26.203500, 28.133500, user_list, nodegroup='MeasurementLabCentos'),
    makesite('lax01','38.98.51.0',     '2001:550:6800::',      'Los Angeles_CA', 'US', 33.942500, -118.407200, user_list, nodegroup='MeasurementLabCentos'),
    makesite('lax02','63.243.240.64',  '2001:5a0:3a01::',      'Los Angeles_CA', 'US', 33.942500, -118.407200, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('lax03','173.205.3.64',   '2001:668:1f:1e::',     'Los Angeles_CA', 'US', 33.942500, -118.407200, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('lax04','4.15.166.0',     '2001:1900:2100:15::',  'Los Angeles_CA', 'US', 33.942500, -118.407200, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('lax05','128.177.109.192','2001:438:fffd:2e::',   'Los Angeles_CA', 'US', 33.942500, -118.407200, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('lba01','109.239.110.0',  '2a00:1a80:1:8::',      'Leeds', 'GB', 53.865800, -1.660560, user_list, nodegroup='MeasurementLabCentos'),
    makesite('lca01','82.116.199.0',   None,                   'Larnaca', 'CY', 34.880900, 33.626000, user_list, exclude=[1,2,3], nodegroup='MeasurementLabCentos'),
    makesite('lga02','38.106.70.128',  '2001:550:1d00:100::',  'New York_NY', 'US', 40.766700, -73.866700, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('lga03','64.86.148.128',  '2001:5a0:4300::',      'New York_NY', 'US', 40.766700, -73.866700, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('lga04','173.205.4.64',   '2001:668:1f:22::',     'New York_NY', 'US', 40.766700, -73.866700, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('lga05','4.35.94.0',      '2001:1900:2100:14::',  'New York_NY', 'US', 40.766700, -73.866700, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('lga06','128.177.119.192','2001:438:fffd:2b::',   'New York_NY', 'US', 40.766700, -73.866700, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('lga07','66.151.223.128', '2600:c0f:2002::',      'New York_NY', 'US', 40.766700, -73.866700, user_list, nodegroup='MeasurementLabCentos'),
    makesite('lhr01','217.163.1.64',   '2001:4c08:2003:3::',   'London', 'GB', 51.469700, -0.451389, user_list, nodegroup='MeasurementLabCentos'),
    makesite('lju01','91.239.96.64',   '2001:67c:27e4:100::',  'Ljubljana', 'SI', 46.223600, 14.457500, user_list, nodegroup='MeasurementLabCentos'),
    makesite('los01','196.216.149.64', None,                   'Lagos', 'NG', 6.5821, 3.3211, user_list, exclude=[1,2,3], arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('mad01','213.200.103.128','2001:668:1f:16::',     'Madrid', 'ES', 40.466700, -3.566670, user_list, nodegroup='MeasurementLabCentos'),
    makesite('mia01','4.71.210.192',   '2001:1900:3001:a::',   'Miami_FL', 'US', 25.783300, -80.266700, user_list, nodegroup='MeasurementLabCentos'),
    makesite('mia02','38.109.21.0',    '2001:550:6c01::',      'Miami_FL', 'US', 25.783300, -80.266700, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('mia03','66.110.73.0',    '2001:5a0:3801::',      'Miami_FL', 'US', 25.783300, -80.266700, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('mia04','173.205.3.128',  '2001:668:1f:1f::',     'Miami_FL', 'US', 25.783300, -80.266700, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('mia05','128.177.109.0',  '2001:438:fffd:29::',   'Miami_FL', 'US', 25.783300, -80.266700, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('mil01','213.200.99.192', '2001:668:1f:17::',     'Milan', 'IT', 45.464000, 9.191600, user_list, nodegroup='MeasurementLabCentos'),
    makesite('mnl01','202.90.156.0',   '2001:d18:0:35::',      'Manila', 'PH', 14.5086, 121.0194, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('nbo01','197.136.0.64',   '2c0f:fe08:10:64::',    'Nairobi', 'KE', -1.319170, 36.925800, user_list, nodegroup='MeasurementLabCentos'),
    makesite('nuq02','149.20.5.64',    '2001:4f8:1:1001::',    'San Francisco Bay Area_CA', 'US', 37.383300, -122.066700, user_list, nodegroup='MeasurementLabCentos'),
    makesite('nuq03','38.102.163.128', '2001:550:1502::',      'San Francisco Bay Area_CA', 'US', 37.383300, -122.066700, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('nuq04','66.110.32.64',   '2001:5a0:3e00::',      'San Francisco Bay Area_CA', 'US', 37.383300, -122.066700, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('nuq05','216.156.85.192', '2610:18:111:7::',      'San Francisco Bay Area_CA', 'US', 37.383300, -122.066700, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('nuq06','128.177.109.128','2001:438:fffd:2d::',   'San Francisco Bay Area_CA', 'US', 37.383300, -122.066700, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('ord01','4.71.251.128',   '2001:1900:3001:b::',   'Chicago_IL', 'US', 41.978600, -87.904700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos'),
    makesite('ord02','38.65.210.192',  '2001:550:1b01:1::',    'Chicago_IL', 'US', 41.978600, -87.904700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos'),
    makesite('ord03','66.198.24.64',   '2001:5a0:4200::',      'Chicago_IL', 'US', 41.978600, -87.904700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos'),
    makesite('ord04','173.205.3.192',  '2001:668:1f:20::',     'Chicago_IL', 'US', 41.978600, -87.904700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos'),
    makesite('ord05','128.177.163.0',  '2001:438:fffd:2f::',   'Chicago_IL', 'US', 41.978600, -87.904700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos'),
    makesite('par01','80.239.168.192', '2001:2030:0:1a::',     'Paris', 'FR', 48.858400, 2.349010, user_list, nodegroup='MeasurementLabCentos'),
    makesite('prg01','212.162.51.64',  '2001:4c08:2003:4::',   'Prague', 'CZ', 50.083300, 14.416700, user_list, count=4, nodegroup='MeasurementLabCentos'),
    makesite('sea01','38.102.0.64',    '2001:550:3200:1::',    'Seattle_WA', 'US', 47.448900, -122.309400, user_list, nodegroup='MeasurementLabCentos'),
    makesite('sea02','63.243.224.0',   '2001:5a0:4400::',      'Seattle_WA', 'US', 47.448900, -122.309400, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('sea03','173.205.3.0',    '2001:668:1f:1d::',     'Seattle_WA', 'US', 47.448900, -122.309400, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('sea04','4.71.157.128',   '2001:1900:2100:16::',  'Seattle_WA', 'US', 47.448900, -122.309400, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('sea05','64.3.225.64',    '2610:18:114:4001::',   'Seattle_WA', 'US', 47.448900, -122.309400, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('sea06','64.74.15.192',   '2600:c00:0:202::',     'Seattle_WA', 'US', 47.448900, -122.309400, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos'),
    makesite('sin01','180.87.97.64',   '2405:2000:301::',      'Singapore', 'SG', 1.3550, 103.9880, user_list, nodegroup='MeasurementLabCentos'),
    makesite('sjc01','70.42.244.64',   '2600:c02:2:82::',      'San Francisco Bay Area_CA', 'US', 37.383300, -122.066700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos'),  # should be nuq07
    makesite('svg01','81.167.39.0',    '2a01:798:0:13::',      'Stavanger', 'NO', 58.876700, 5.63780, user_list, nodegroup='MeasurementLabCentos'),
    makesite('syd01','203.5.76.128',   '2001:388:d0::',        'Sydney', 'AU', -33.946100, 151.177000, user_list, nodegroup='MeasurementLabCentos'),
    makesite('syd02','175.45.79.0',    '2402:7800:0:12::',     'Sydney', 'AU', -33.946100, 151.177000, user_list, nodegroup='MeasurementLabCentos'),
    makesite('tnr01','41.188.12.64',   None,                   'Antananarivo', 'MG', -18.7969, 47.4788, user_list, exclude=[1,2,3], arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('tpe01','163.22.28.0',    '2001:e10:6840:28::',   'Taipei', 'TW', 25.077800, 121.224000, user_list, nodegroup='MeasurementLabCentos'),
    makesite('trn01','194.116.85.192', '2001:7f8:23:307::',    'Turin', 'IT', 45.200800, 7.649720, user_list, nodegroup='MeasurementLabCentos'),
    # old ipv6 2c0f:fab0:ffff:1000:: @ tun01
    makesite('tun01','41.231.21.0',    '2001:4350:3000:1::',   'Tunis', 'TN', 36.851600, 10.229100, user_list, nodegroup='MeasurementLabCentos'),
    makesite('vie01','213.208.152.0',  '2a01:190:1700:38::',   'Vienna', 'AT', 48.269000, 16.410700, user_list, nodegroup='MeasurementLabCentos'),
    makesite('wlg02','163.7.129.64',   '2404:138:4009:1::',    'Wellington', 'NZ', -41.327200, 174.805000, user_list, nodegroup='MeasurementLabCentos'),
    makesite('yul01','162.219.49.0',   '2620:10a:80fe::',      'Montreal', 'CA', 45.4576, -73.7497, user_list, arch='x86_64-r420', nodegroup='MeasurementLabCentos'),
    makesite('yyc01','162.219.50.0',   '2620:10a:80ff::',      'Calgary', 'CA', 51.1315, -114.0106, user_list, arch='x86_64-r420', nodegroup='MeasurementLabCentos'),
    makesite('yyz01','162.219.48.0',   '2620:10a:80fd::',      'Toronto', 'CA', 43.6767, -79.6306, user_list, arch='x86_64-r420', nodegroup='MeasurementLabCentos'),

    # Site for M-Lab testing machines
    makesite('lga0t','4.14.159.64', '2001:1900:2100:2d::','New York_NY', 'US', 40.766700, -73.866700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos'),
    makesite('lga1t','4.14.3.0',    '2001:1900:2100:1::', 'New York_NY', 'US', 40.766700, -73.866700, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('nuq0t','23.228.128.0',   '2605:a601:f1ff:fffd::', None, None, 0,0, user_list, count=4, nodegroup='MeasurementLabCentos'),
    makesite('nuq1t','23.228.128.128', '2605:a601:f1ff:ffff::','San Francisco Bay Area_CA', 'US', 37.383300, -122.066700, user_list, count=4, nodegroup='MeasurementLabCentos'),
    makesite('iad0t','165.117.251.128', '2610:18:8b40:200::','Washington_DC', 'US', 38.944400, -77.455800, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos'),
    makesite('iad1t','165.117.240.0', '2610:18:8b40:202::','Washington_DC', 'US', 38.944400, -77.455800, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos'),
   # NOTE: mlc servers need special handling
   #Site(name='mlc',   net=Network(v4='64.9.225.64',     v6='2604:CA00:F000:5::'), domain="measurementlab.net", count=3),
]

