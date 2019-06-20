#!/usr/bin/python

from planetlab.model import *
from users import user_list

# NOTE: The legacy network remap is used to re-order the automatically
#   generated, sequential list of ipaddresses to a legacy order to preserve
#   pre-existing slice-and-IP assignments.  Otherwise, slices would be assigned
#   to new IPs, and for now, we wish to preserve the slice-node-ip mapping.
# An appropriate time to remove this and re-assign IPs to slices would be
#   after a major update & reinstallation, such as LXC kernel update.
legacy_network_remap = {}
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
    makesite('akl01','163.7.129.0',    '2404:138:4009::',      'Auckland', 'NZ', -36.850000, 174.783000, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('ams03','80.239.169.0',   '2001:2030:32::',       'Amsterdam', 'NL', 52.308600, 4.763890, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('ams04','77.67.114.64',   '2001:668:1f:5f::',     'Amsterdam', 'NL', 52.308600, 4.763890, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('ams05','195.89.145.0',   '2001:5002:100:21::',   'Amsterdam', 'NL', 52.308600, 4.763890, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('ams07','31.186.242.0',   '2a02:b50:4020:cfb1::', 'Amsterdam', 'NL', 52.308600, 4.763890, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('ams08','213.244.128.128','2001:4c08:2003:2::',   'Amsterdam', 'NL', 52.308600, 4.763890, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('arn02','195.89.146.192', '2001:5012:100:24::',   'Stockholm', 'SE', 59.651900, 17.918600, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('arn03','213.242.86.64',  '2001:4c08:2003:44::',  'Stockholm', 'SE', 59.651900, 17.918600, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('arn04','62.115.225.128', '2001:2030:0:38::',     'Stockholm', 'SE', 59.651900, 17.918600, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('arn05','77.67.119.64',   '2001:668:1f:6a::',     'Stockholm', 'SE', 59.651900, 17.918600, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('ath03','193.201.166.128', '2001:648:25e0::',     'Athens', 'GR', 37.936400, 23.944400, user_list, count=4, arch='x86_64-r630', v6gw='2001:648:25e0::129', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('atl02','38.112.151.64',  '2001:550:5b00:1::',    'Atlanta_GA', 'US', 33.636700, -84.428100, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('atl03','64.86.200.192',  '2001:5a0:3b02::',      'Atlanta_GA', 'US', 33.636700, -84.428100, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('atl04','173.205.0.192',  '2001:668:1f:1c::',     'Atlanta_GA', 'US', 33.636700, -84.428100, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('atl06','70.42.177.64',   '2600:c0b:2002:5::',    'Atlanta_GA', 'US', 33.636700, -84.428100, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('atl07','209.170.91.128',   '2001:2030:0:42::',    'Atlanta_GA', 'US', 33.636700, -84.428100, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('atl08','4.71.254.128',   '2001:1900:3001:c::',   'Atlanta_GA', 'US', 33.636700, -84.428100, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('bcn01','91.213.30.192',   '2001:67c:137c:5::',   'Barcelona', 'ES', 41.297445, 2.081105, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('beg01','188.120.127.0',  '2001:7f8:1e:6::',      'Belgrade', 'RS', 44.821600, 20.292100, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('bom01','125.18.112.64',  '2404:a800:2000:217::', 'Mumbai', 'IN', 19.088611, 72.868056, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('bom02','14.143.58.128',  '2403:0:100:66::',      'Mumbai', 'IN', 19.088611, 72.868056, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('bru01','195.89.146.128', '2001:5005:200::',      'Brussels', 'BE', 50.4974163, 3.3528346, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('bru02','212.3.248.192',  '2001:4c08:2003:45::',  'Brussels', 'BE', 50.4974163, 3.3528346, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('bru03','62.115.229.192', '2001:2030:0:39::',     'Brussels', 'BE', 50.4974163, 3.3528346, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('bru04','77.67.119.0',    '2001:668:1f:69::',     'Brussels', 'BE', 50.4974163, 3.3528346, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('cpt01','154.114.19.64',  '2001:4200:0:e::',      'Cape_Town', 'ZA', -33.972387,18.601803, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('den02','4.34.58.0',      '2001:1900:2200:49::',  'Denver_CO', 'US', 39.856100, -104.673700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('den04','128.177.109.64', '2001:438:fffd:2c::',   'Denver_CO', 'US', 39.856100, -104.673700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('den05','209.170.120.64', '2001:2030:0:3b::',     'Denver_CO', 'US', 39.856100, -104.673700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('dfw02','64.86.132.64',   '2001:5a0:3f00::',      'Dallas_TX', 'US', 32.896900, -97.038100, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('dfw03','4.15.35.128',    '2001:1900:2200:44::',  'Dallas_TX', 'US', 32.896900, -97.038100, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('dfw05','128.177.163.64', '2001:438:fffd:30::',   'Dallas_TX', 'US', 32.896900, -97.038100, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('dfw06','63.251.44.192',  '2600:c12:1002:4::',    'Dallas_TX', 'US', 32.896900, -97.038100, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('dfw07','209.170.119.128','2001:2030:0:1f::',     'Dallas_TX', 'US', 32.896900, -97.038100, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('dfw08','38.107.216.0',   '2001:550:2000::',      'Dallas_TX', 'US', 32.896900, -97.038100, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('dub01','193.1.12.192',   '2001:770:b5::',        'Dublin', 'IE', 53.433300, -6.250000, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('fln01','200.237.203.0',  '2801:80:a88:4006::',   'Florianopolis', 'BR', -27.668455, -48.545998, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('fra01','80.239.199.0',   '2001:2030:2f::',       'Frankfurt', 'DE', 50.037932, 8.562151, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('fra02','77.67.114.0',    '2001:668:1f:5e::',     'Frankfurt', 'DE', 50.037932, 8.562151, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('fra03','195.89.146.64',  '2001:5001:200:30::',   'Frankfurt', 'DE', 50.037932, 8.562151, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('fra04','62.67.198.192',  '2001:4c08:2003:40::',  'Frankfurt', 'DE', 50.037932, 8.562151, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('ham02','80.239.142.192', '2001:2030:0:19::',     'Hamburg', 'DE', 53.633300, 9.983330, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    # NOTE: hnd01's arch is 'x86_64-r630', but they are actually R620s. The boot flags and CD for the R630s works for the R620s, whereas the arch 'x86_64' does not.
    makesite('hnd01','203.178.130.192','2001:200:0:b801::',    'Tokyo', 'JP', 35.552200, 139.780000, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('hnd02','210.151.179.128','2001:260:8a::',        'Tokyo', 'JP', 35.552200, 139.780000, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('iad02','38.90.140.128',  '2001:550:200:7::',     'Washington_DC', 'US', 38.944400, -77.455800, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('iad03','66.198.10.128',  '2001:5a0:3c03::',      'Washington_DC', 'US', 38.944400, -77.455800, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('iad04','173.205.4.0',    '2001:668:1f:21::',     'Washington_DC', 'US', 38.944400, -77.455800, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('iad05','4.35.238.192',   '2001:1900:2200:46::',  'Washington_DC', 'US', 38.944400, -77.455800, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('iad06','209.170.119.192','2001:2030:0:29::',     'Washington_DC', 'US', 38.944400, -77.455800, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('jnb01','196.24.45.128',  '2001:4200:fff0:4512::','Johannesburg', 'ZA', -26.203500, 28.133500, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('lax02','63.243.240.64',  '2001:5a0:3a01::',      'Los Angeles_CA', 'US', 33.942500, -118.407200, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('lax03','173.205.3.64',   '2001:668:1f:1e::',     'Los Angeles_CA', 'US', 33.942500, -118.407200, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('lax04','4.15.166.0',     '2001:1900:2100:15::',  'Los Angeles_CA', 'US', 33.942500, -118.407200, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('lax05','128.177.109.192','2001:438:fffd:2e::',   'Los Angeles_CA', 'US', 33.942500, -118.407200, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('lax06','38.98.51.0',     '2001:550:6800::',      'Los Angeles_CA', 'US', 33.942500, -118.407200, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('lca01','82.116.199.0',   None,                   'Larnaca', 'CY', 34.880900, 33.626000, user_list, exclude=[1,2,3], nodegroup='MeasurementLabCentos', roundrobin=False),
    makesite('lga03','64.86.148.128',  '2001:5a0:4300::',      'New York_NY', 'US', 40.766700, -73.866700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('lga04','173.205.4.64',   '2001:668:1f:22::',     'New York_NY', 'US', 40.766700, -73.866700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('lga05','4.35.94.0',      '2001:1900:2100:14::',  'New York_NY', 'US', 40.766700, -73.866700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('lga06','128.177.119.192','2001:438:fffd:2b::',   'New York_NY', 'US', 40.766700, -73.866700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('lga07','66.151.223.128', '2600:c0f:2002::',      'New York_NY', 'US', 40.766700, -73.866700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('lga08','38.106.70.128',  '2001:550:1d00:100::',  'New York_NY', 'US', 40.766700, -73.866700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('lhr02','80.239.170.192', '2001:2030:33::',       'London', 'GB', 51.469700, -0.451389, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('lhr03','77.67.114.192',  '2001:668:1f:61::',     'London', 'GB', 51.469700, -0.451389, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('lhr04','195.89.146.0',  '2001:5000:1100:31::',   'London', 'GB', 51.469700, -0.451389, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('lhr05','212.113.31.0',  '2001:4c08:2003:3c::',   'London', 'GB', 51.469700, -0.451389, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('lis01','213.242.96.192',  '2001:4c08:2003:3d::', 'Lisbon', 'PT', 38.775600, -9.135400, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('lis02','195.89.147.128',  '2001:500d:200:3::',   'Lisbon', 'PT', 38.775600, -9.135400, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('lju01','91.239.96.64',   '2001:67c:27e4:100::',  'Ljubljana', 'SI', 46.223600, 14.457500, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('mad02','213.242.96.128','2001:4c08:2003:3e::',   'Madrid', 'ES', 40.466700, -3.566670, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('mad03','80.239.229.128','2001:2030:34::',        'Madrid', 'ES', 40.466700, -3.566670, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('mad04','77.67.115.64',  '2001:668:1f:63::',      'Madrid', 'ES', 40.466700, -3.566670, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('mia02','38.109.21.0',    '2001:550:6c01::',      'Miami_FL', 'US', 25.783300, -80.266700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('mia03','66.110.73.0',    '2001:5a0:3801::',      'Miami_FL', 'US', 25.783300, -80.266700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('mia04','173.205.3.128',  '2001:668:1f:1f::',     'Miami_FL', 'US', 25.783300, -80.266700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('mia05','128.177.109.0',  '2001:438:fffd:29::',   'Miami_FL', 'US', 25.783300, -80.266700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('mia06','4.71.210.192',   '2001:1900:3001:a::',   'Miami_FL', 'US', 25.783300, -80.266700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('mil02','80.239.222.0',   '2001:2030:30::',       'Milan', 'IT', 45.464000, 9.191600, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('mil03','77.67.115.0',    '2001:668:1f:62::',     'Milan', 'IT', 45.464000, 9.191600, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('mil04','213.242.77.128', '2001:1900:2200:af::',  'Milan', 'IT', 45.464000, 9.191600, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('mil05','195.89.147.0',   '2001:5008:100:14::',   'Milan', 'IT', 45.464000, 9.191600, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('mnl01','202.90.156.0',   '2001:d18:0:35::',      'Manila', 'PH', 14.5086, 121.0194, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('mpm01','41.94.23.0',      None,                  'Maputo', 'MZ', -25.9208, 32.5725, user_list, count=4, arch='x86_64-r630', exclude=[1,2,3,4], nodegroup='MeasurementLabCentos', roundrobin=False),
    makesite('nbo01','197.136.0.64',   '2c0f:fe08:10:64::',    'Nairobi', 'KE', -1.319170, 36.925800, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('nuq02','149.20.5.64',    '2001:4f8:1:1001::',    'San Francisco Bay Area_CA', 'US', 37.383300, -122.066700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('nuq03','38.102.163.128', '2001:550:1502::',      'San Francisco Bay Area_CA', 'US', 37.383300, -122.066700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('nuq04','66.110.32.64',   '2001:5a0:3e00::',      'San Francisco Bay Area_CA', 'US', 37.383300, -122.066700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('nuq06','128.177.109.128','2001:438:fffd:2d::',   'San Francisco Bay Area_CA', 'US', 37.383300, -122.066700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('nuq07','209.170.110.192','2001:2030:0:12::',     'San Francisco Bay Area_CA', 'US', 37.383300, -122.066700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('ord02','38.65.210.192',  '2001:550:1b01:1::',    'Chicago_IL', 'US', 41.978600, -87.904700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('ord03','66.198.24.64',   '2001:5a0:4200::',      'Chicago_IL', 'US', 41.978600, -87.904700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('ord04','173.205.3.192',  '2001:668:1f:20::',     'Chicago_IL', 'US', 41.978600, -87.904700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('ord05','128.177.163.0',  '2001:438:fffd:2f::',   'Chicago_IL', 'US', 41.978600, -87.904700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('ord06','4.71.251.128',   '2001:1900:3001:b::',   'Chicago_IL', 'US', 41.978600, -87.904700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('par02','212.73.231.192', '2001:4c08:2003:3f::',  'Paris', 'FR', 48.858400, 2.349010, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('par03','80.239.222.64',  '2001:2030:35::',       'Paris', 'FR', 48.858400, 2.349010, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('par04','77.67.119.128',  '2001:668:1f:6b::',     'Paris', 'FR', 48.858400, 2.349010, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('par05','195.89.147.192', '2001:5003:300:e::',    'Paris', 'FR', 48.858400, 2.349010, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('prg02','195.122.159.128','2001:4c08:2003:42::',  'Prague', 'CZ', 50.083300, 14.416700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('prg03','80.239.156.128', '2001:2030:31::',       'Prague', 'CZ', 50.083300, 14.416700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('prg04','77.67.114.128',  '2001:668:1f:60::',     'Prague', 'CZ', 50.083300, 14.416700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('prg05','195.89.147.64',  '2001:5016:100:3::',    'Prague', 'CZ', 50.083300, 14.416700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('sea02','63.243.224.0',   '2001:5a0:4400::',      'Seattle_WA', 'US', 47.448900, -122.309400, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('sea03','173.205.3.0',    '2001:668:1f:1d::',     'Seattle_WA', 'US', 47.448900, -122.309400, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('sea04','4.71.157.128',   '2001:1900:2100:16::',  'Seattle_WA', 'US', 47.448900, -122.309400, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('sea06','64.74.15.192',   '2600:c00:0:202::',     'Seattle_WA', 'US', 47.448900, -122.309400, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('sea07','209.170.110.128','2001:2030:0:a::',      'Seattle_WA', 'US', 47.448900, -122.309400, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('sea08','38.102.0.64',    '2001:550:3200:1::',    'Seattle_WA', 'US', 47.448900, -122.309400, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('sin01','180.87.97.64',   '2405:2000:301::',      'Singapore', 'SG', 1.3550, 103.9880, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('sjc01','70.42.244.64',   '2600:c02:2:82::',      'San Francisco Bay Area_CA', 'US', 37.383300, -122.066700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),  # should be nuq07
    makesite('svg01','81.167.39.0',    '2a01:798:0:13::',      'Stavanger', 'NO', 58.876700, 5.63780, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('syd02','175.45.79.0',    '2402:7800:0:12::',     'Sydney', 'AU', -33.946100, 151.177000, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('syd03','203.5.76.128',   '2001:388:d0::',        'Sydney', 'AU', -33.946100, 151.177000, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('tgd01','213.149.127.0',  '2a00:fe80:0:104::',    'Podgorica', 'ME', 42.107764, 18.761649, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('tnr01','41.188.12.64',   None,                   'Antananarivo', 'MG', -18.7969, 47.4788, user_list, exclude=[1,2,3,4], count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('tpe01','163.22.28.0',    '2001:e10:6840:28::',   'Taipei', 'TW', 25.077800, 121.224000, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('trn01','194.116.85.192', '2001:7f8:23:307::',    'Turin', 'IT', 45.200800, 7.649720, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    # old ipv6 2c0f:fab0:ffff:1000:: @ tun01
    makesite('tun01','41.231.21.0',    '2001:4350:3000:1::',   'Tunis', 'TN', 36.851600, 10.229100, user_list, count=4, arch='x86_64-r630',  nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('vie01','213.208.152.0',  '2a01:190:1700:38::',   'Vienna', 'AT', 48.269000, 16.410700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('wlg02','163.7.129.64',   '2404:138:4009:1::',    'Wellington', 'NZ', -41.327200, 174.805000, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('yqm01','209.51.169.128', '2001:470:1:820::',     'Moncton', 'CA', 46.107332, -64.673830, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('yul02','216.66.14.64',   '2001:470:1:48f::',     'Montreal', 'CA', 45.4576, -73.7497, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('yvr01','184.105.70.192', '2001:470:1:822::',     'Vancouver','CA', 49.190165, -123.183665, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('ywg01','184.105.55.64',  '2001:470:1:81f::',     'Winnipeg', 'CA', 49.905996, -97.237332, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('yyc02','65.49.72.192',   '2001:470:1:42c::',     'Calgary', 'CA', 51.1315, -114.0106, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('yyz02','216.66.68.128',  '2001:470:1:70a::',     'Toronto', 'CA', 43.6767, -79.6306, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),

    # Site for M-Lab testing machines
    makesite('lga0t','4.14.159.64', '2001:1900:2100:2d::','New York_NY', 'US', 40.766700, -73.866700, user_list, count=4, arch='x86_64-r630', nodegroup='MeasurementLabCentos', roundrobin=True),
    makesite('lga1t','4.14.3.0',    '2001:1900:2100:1::', 'New York_NY', 'US', 40.766700, -73.866700, user_list, count=4, arch='x86_64', nodegroup='MeasurementLabCentos', roundrobin=False),
]

