#!/usr/bin/env python

import json
import optparse
import os
import re
import StringIO
import sys
import time


def usage():
    return """
DESCRIPTION:
    mlabconfig.py generates legacy config files in various formats from M-Lab
    sites & experiments configuration.

EXAMPLES:
    mlabconfig.py --format=hostips
      (e.g. mlab-host-ips.txt)

    mlabconfig.py --format=sitestats
      (e.g. mlab-site-stats.json)

TODO:
    mlabconfig.py --format=zone
      (e.g. gen_zones.py)
"""


def parse_flags():
    parser = optparse.OptionParser(usage=usage())
    parser.add_option(
        '', '--sites_config', metavar='sites', dest='sites_config',
        default='sites', help='The name of the module with Site() definitions.')
    parser.add_option(
        '', '--experiments_config', metavar='slices', dest='experiments_config',
        default='slices',
        help='The name of the module with Slice() definitions.')
    parser.add_option(
        '', '--sites', metavar='sites', dest='sites', default='site_list',
        help='The variable name of sites within the sites_config data.')
    parser.add_option(
        '', '--experiments', metavar='experiments', dest='experiments',
        default='slice_list',
        help=('The variable name of experiments within the experiments_config '
              'data.'))
    # TODO: Support multiple formats, e.g. 'hostips', 'zone', 'sitestats'.
    parser.add_option(
        '', '--format', metavar='format', dest='format', default='hostips',
        help='Format of output.')
    return parser.parse_args()


def export_mlab_site_stats(output, sites):
    sitestats = []
    for site in sites:
        name = site['name']
        location = site['location']
        if location is None:
            location = {
                'city': '', 'country': '', 'latitude': None, 'longitude': None}
        metro = [name, name[:-2]]
        sitestats.append({
            'site': name,
            'metro': metro,
            'city': location['city'],
            'country': location['country'],
            'latitude': location['latitude'],
            'longitude': location['longitude']})
    json.dump(sitestats, output)


def export_mlab_host_ips(output, sites, experiments):
    """Writes csv data of all M-Lab servers and experiments to output."""
    # Export server names and addresses.
    for site in sites:
        # TODO(soltesz): change 'nodes' to be a sorted list of node objects.
        for _, node in site['nodes'].iteritems():
            output.write('{name},{ipv4},{ipv6}\n'.format(
                name=node.hostname(), ipv4=node.ipv4(), ipv6=node.ipv6()))

    # Export experiment names and addresses.
    for experiment in experiments:
        # TODO(soltesz): change 'network_list' to a sorted list of node objects.
        for _, node in experiment['network_list']:
            if experiment['index'] is None:
                # Ignore experiments without an IP address.
                continue
            output.write('{name},{ipv4},{ipv6}\n'.format(
                name=experiment.hostname(node), ipv4=experiment.ipv4(node),
                ipv6=experiment.ipv6(node)))


def main():
    (options, args) = parse_flags()

    # TODO: consider alternate formats for configuration information, e.g. yaml.
    sites = getattr(__import__(options.sites_config), options.sites)
    experiments = getattr(
        __import__(options.experiments_config), options.experiments)

    # Assign every slice to every node.
    for experiment in experiments:
        for site in sites:
            for hostname, node in site['nodes'].iteritems():
                experiment.add_node_address(node)

    if options.format == 'hostips':
        export_mlab_host_ips(sys.stdout, sites, experiments)
    elif options.format == 'sitestats':
        export_mlab_site_stats(sys.stdout, sites)
    elif options.format == 'zone':
        print 'Sorry, mlabconfig does not yet support generating zone files.'
        sys.exit(1)
    else:
        print 'Sorry, unknown format: %s' % options.format
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, IOError):
        pass
