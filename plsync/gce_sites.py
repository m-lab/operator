from planetlab.model import *
from users import user_list

site_list = [
    makesite('tyo01', '35.200.102.226', None, 'Tokyo', 'JP', 35.552200, 139.780000, [], exclude=[1], count=1, arch='x86_64', nodegroup='GCEVM', gcenet=True),
    makesite('tyo02', '35.200.34.149', None, 'Tokyo', 'JP', 35.552200, 139.780000, [], exclude=[1], count=1, arch='x86_64', nodegroup='GCEVM', gcenet=True),
    makesite('tyo03', '35.200.112.17', None, 'Tokyo', 'JP', 35.552200, 139.780000, [], exclude=[1], count=1, arch='x86_64', nodegroup='GCEVM', gcenet=True),
]
