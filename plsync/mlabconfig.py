#!/usr/bin/env python

import json
import logging
import optparse
import os
import re
import StringIO
import sys
import time

ZONE_TTL = 60 * 5
ZONE_MIN_TTL = 60 * 5
ZONE_REFRESH = 60 * 60
ZONE_RETRY = 60 * 10
ZONE_EXPIRE = 7 * 60 * 60 * 24
ZONE_HEADER_TEMPLATE = 'mlabzone.header.in'
ZONE_SERIAL_COUNTER = '/tmp/mlabconfig.serial'


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

    mlabconfig.py --format=zone
      (e.g. gen_zones.py)
"""


def parse_flags():
    parser = optparse.OptionParser(usage=usage())
    parser.set_defaults(force=False,
                        support_email='support.measurementlab.net',
                        primary_nameserver='sns-pb.isc.org',
                        secondary_nameserver='ns-mlab.greenhost.net',
                        domain='measurement-lab.org',
                        serial='auto',
                        zonefile=None,
                        ttl=ZONE_TTL,
                        minttl=ZONE_MIN_TTL,
                        refresh=ZONE_REFRESH,
                        retry=ZONE_RETRY,
                        expire=ZONE_EXPIRE)

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
    parser.add_option(
        '', '--format', metavar='format', dest='format', default='hostips',
        help='Format of output.')
    parser.add_option(
        '', '--zoneheader', metavar='zoneheader.in', dest='zoneheader',
        default=ZONE_HEADER_TEMPLATE,
        help='The full path to zone header file.')

    (options, args) = parse_flags()

    # Check given parameters.
    if options.format == 'zone' and not os.path.exists(options.zoneheader):
        logging.error('Zone header file %s not found!', options.zoneheader)
        sys.exit(1)

    return (options, args)


def comment(output, note):
    output.write('\n; %s\n' % note)


def write_a_record(output, hostname, ipv4):
    output.write(format_a_record(hostname, ipv4))
    output.write('\n')


def format_a_record(hostname, ipv4):
    return '%-32s  IN  A   \t%s' % (hostname, ipv4)


def write_aaaa_record(output, hostname, ipv6):
    output.write(format_aaaa_record(hostname, ipv6))
    output.write('\n')


def format_aaaa_record(hostname, ipv6):
    return '%-32s  IN  AAAA\t%s' % (hostname, ipv6)


def export_router_and_switch_records(output, sites):
    comment(output, 'router and switch v4 records.')
    for i, site in enumerate(sites):
        write_a_record(output, 'r1.' + site['name'], site.ipv4(index=1))
        write_a_record(output, 's1.' + site['name'], site.ipv4(index=2))


def export_pcu_records(output, sites):
    comment(output, 'pcus v4')
    for site in sites:
        # TODO: change site['nodes'] to a pre-sorted list type.
        for node in sorted(site['nodes'].values(), key=lambda n: n.hostname()):
            write_a_record(output, node['pcu'].recordname(), node['pcu'].ipv4())


def export_server_records(output, sites):
    export_server_records_v4(output, sites)
    export_server_records_v4(output, sites, decoration='v4')
    export_server_records_v6(output, sites)
    export_server_records_v6(output, sites, decoration='v6')


def export_server_records_v4(output, sites, decoration=''):
    comment(output, 'hosts v4%s' % (' decorated' if decoration else ''))
    for site in sites:
        # TODO: change site['nodes'] to a pre-sorted list type.
        for node in sorted(site['nodes'].values(), key=lambda n: n.hostname()):
            write_a_record(output, node.recordname(decoration), node.ipv4())


def export_server_records_v6(output, sites, decoration=''):
    comment(output, 'hosts v6%s' % (' decorated' if decoration else ''))
    for site in sites:
        # TODO: change site['nodes'] to a pre-sorted list type.
        for node in sorted(site['nodes'].values(), key=lambda n: n.hostname()):
            if node.ipv6_is_enabled():
                write_aaaa_record(
                    output, node.recordname(decoration), node.ipv6())


def export_experiment_records(output, sites, experiments):
    for experiment in experiments:
        if experiment['index'] is None:
            # Ignore experiments without an IP address.
            continue
        export_experiment_records_v4(output, sites, experiment)
        export_experiment_records_v4(output, sites, experiment, decoration='v4')

        export_experiment_records_v6(output, sites, experiment)
        export_experiment_records_v6(output, sites, experiment, decoration='v6')


def export_experiment_records_v4(output, sites, experiment, decoration=''):
    comment(output, '%s v4%s' % (experiment.dnsname(), (
        ' decorated' if decoration else '')))
    for site in sites:
        # TODO: change site['nodes'] to a pre-sorted list type.
        for node in sorted(site['nodes'].values(), key=lambda n: n.hostname()):
            # TODO: remove sitenames (or exclude mlab4's).
            write_a_record(output, experiment.sitename(node, decoration),
                           experiment.ipv4(node))
            write_a_record(output, experiment.recordname(node, decoration),
                           experiment.ipv4(node))


def export_experiment_records_v6(output, sites, experiment, decoration=''):
    comment(output, '%s v6%s' % (experiment.dnsname(), (
        ' decorated' if decoration else '')))
    for site in sites:
        # TODO: change site['nodes'] to a pre-sorted list type.
        for node in sorted(site['nodes'].values(), key=lambda n: n.hostname()):
            # TODO: remove sitenames (or exclude mlab4's).
            if (node.ipv6_is_enabled() and experiment.ipv6(node)):
                write_aaaa_record(output, experiment.sitename(node, decoration),
                                  experiment.ipv6(node))
                write_aaaa_record(output, experiment.recordname(
                    node,decoration), experiment.ipv6(node))


def export_mlab_zone_records(output, sites, experiments):
    export_router_and_switch_records(output, sites)
    export_pcu_records(output, sites)
    export_server_records(output, sites)
    export_experiment_records(output, sites, experiments)


def get_revision(prefix, revision_path):
    """Returns a two digit revision number as a string.

    The same revision_path should be provided for each call. If the prefix
    matches the previous prefix, then revision number is incremented by one and
    returned, otherwise, the revision is zero ("00"). However, the revision
    number never increases beyond "99".

    Args:
        prefix: str, current date prefix as YYYYMMDD.
        revision_path: str, the full path to a temporary file to read previous
            and store latest revision number.

    Returns:
        str, a two digit revision number, e.g. "00", "01", etc, up to "99".
    """
    n = {'prefix': prefix, 'revision': 0}
    if os.path.exists(revision_path):
        with open(revision_path) as f:
            try:
                n = json.loads(f.read())
                if n['prefix'] == prefix:
                    # Increment previous revision, since prefix is the same.
                    if n['revision'] < 99:
                        n['revision'] += 1
                    else:
                        logging.error('Revision is too large to increase!')
                else:
                    # Reset prefix and revision.
                    n['prefix'] = prefix
                    n['revision'] = 0
            except ValueError:
                logging.error('Content of %s is corrupted', revision_path)

    revision = '%02d' % n['revision']
    with open(revision_path, 'w') as f:
        f.write(json.dumps(n))

    return revision


def serial_rfc1912(ts):
    """Returns an rfc1912 style serial id (YYYYMMDDnn) for a DNS zone file."""
    # RFC1912 (http://www.ietf.org/rfc/rfc1912.txt) recommends 'nn' as the
    # revision. However, identifying and incrementing this value is a manual,
    # error prone step. Instead, we save a temporary daily sequence counter.
    serial_prefix = time.strftime('%Y%m%d', ts)
    return serial_prefix + get_revision(serial_prefix, ZONE_SERIAL_COUNTER)


def export_mlab_zone_header(output, header, options):
    """Writes the zone header file to output.

    Data read from header is used as a template and populated with values from
    options. The end result is written to output.

    Args:
        output: file, a file object open for writing.
        header: file, a file object open for reading.
        options: optparse.Values, all command line options.
    """
    headerdata = header.read()
    headerdata = headerdata % options.__dict__
    output.write(headerdata)


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
        with open(options.zoneheader, 'r') as header:
            if options.serial == 'auto':
                options.serial = serial_rfc1912(time.gmtime())
            export_mlab_zone_header(sys.stdout, header, options)
            sys.stdout.write("\n\n")
            export_mlab_zone_records(sys.stdout, sites, experiments)
    else:
        logging.error('Sorry, unknown format: %s', options.format)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, IOError):
        pass
