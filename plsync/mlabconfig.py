#!/usr/bin/env python

import json
import logging
import optparse
import os
import re
import string
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
SSL_EXPERIMENTS = ['iupui_ndt']


class BracketTemplate(string.Template):
    """Process templates using variable delimiters like: {{var}}.

    The default string.Template delimiter is "$". This makes it difficult to
    make templates from shell scripts or ipxe scripts (which contain many
    natural "$" characters).

    BracketTemplate uses a beginning ("{{") and ending delimiter ("}}"), that
    does not conflict with the syntax of these languages.
    """

    delimiter = '{{'
    pattern = r'''
        \{\{(?:
        (?P<escaped>\{\{)|
        (?P<named>[_a-z][_a-z0-9]*)\}\}|
        (?P<braced>[_a-z][_a-z0-9]*)\}\}|
        (?P<invalid>)
        )'''


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

    mlabconfig.py --format=server-network-config  \
        --template_input=file.template \
        --template_output="$PATH/file-{{hostname}}.xyz" \
        --select=".*iad1t.*"
      (e.g. stage1-$HOSTNAME.ipxe)

    mlabconfig.py --format=scraper_kubernetes \
        --template_input=deploy.yml \
        --template_output=deployment/{{site}}-{{node}}-{{experiment}}-{{rsync_module}}.yml

    mlabconfig.py --format=legacy_prometheus --select="npad.iupui.*"
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

    parser.add_option('',
                      '--sites_config',
                      metavar='sites',
                      dest='sites_config',
                      default='sites',
                      help='The name of the module with Site() definitions.')
    parser.add_option('',
                      '--experiments_config',
                      metavar='slices',
                      dest='experiments_config',
                      default='slices',
                      help='The name of the module with Slice() definitions.')
    parser.add_option(
        '',
        '--sites',
        metavar='sites',
        dest='sites',
        default='site_list',
        help='The variable name of sites within the sites_config data.')
    parser.add_option(
        '',
        '--experiments',
        metavar='experiments',
        dest='experiments',
        default='slice_list',
        help=('The variable name of experiments within the experiments_config '
              'data.'))
    parser.add_option('',
                      '--format',
                      metavar='format',
                      dest='format',
                      default='hostips',
                      help='Format of output.')
    parser.add_option('',
                      '--zoneheader',
                      metavar='zoneheader.in',
                      dest='zoneheader',
                      default=ZONE_HEADER_TEMPLATE,
                      help='The full path to zone header file.')
    parser.add_option(
        '',
        '--template_input',
        dest='template',
        default=None,
        help='Template to apply values. Creates a new file for every hostname.')
    parser.add_option(
        '',
        '--template_output',
        dest='filename',
        default=None,
        help=('Filename interpreted as a template where interpreted template '
              'files are written.'))
    parser.add_option(
        '',
        '--select',
        dest='select',
        default=None,
        help=('A regular expression used to select a subset of hostnames. If '
              'not specified, all machine names are selected.'))

    (options, args) = parser.parse_args()

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


def flatten_hostname(hostname):
    """Converts subdomains to flat names suitable for SSL certificate wildcards.

    For example, convert 'ndt.iupui.mlab1.nuq1t' to 'ndt-iupui-mlab1-nuq1t'

    Args:
      hostname: str, the dotted subdomain to flatten

    Returns:
      str, the modified hostname
    """
    return hostname.replace('.', '-')


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
                write_aaaa_record(output, node.recordname(decoration),
                                  node.ipv6())


def export_experiment_records(output, sites, experiments):
    for experiment in experiments:
        if experiment['index'] is None:
            # Ignore experiments without an IP address.
            continue
        export_experiment_records_v4(output, sites, experiment)
        export_experiment_records_v4(output, sites, experiment, decoration='v4')

        export_experiment_records_v6(output, sites, experiment)
        export_experiment_records_v6(output, sites, experiment, decoration='v6')

        # Create "flattened" domain names for SSL enabled experiments so that
        # certificate wildcard matching works. See flatten_hostname().
        if experiment['name'] in SSL_EXPERIMENTS:
            export_experiment_records_v4(
                output, sites, experiment, decoration='', flatnames=True)
            export_experiment_records_v4(
                output, sites, experiment, decoration='v4', flatnames=True)
            export_experiment_records_v6(
                output, sites, experiment, decoration='', flatnames=True)
            export_experiment_records_v6(
                output, sites, experiment, decoration='v6', flatnames=True)


def export_experiment_records_v4(output,
                                 sites,
                                 experiment,
                                 decoration='',
                                 flatnames=False):
    comment(output, '%s v4%s%s' % (experiment.dnsname(), (
        ' decorated' if decoration else ''), (' flattened'
                                              if flatnames else '')))
    for site in sites:
        # TODO: change site['nodes'] to a pre-sorted list type.
        for node in sorted(site['nodes'].values(), key=lambda n: n.hostname()):
            # TODO: remove sitenames (or exclude mlab4's).
            sitename = experiment.sitename(node, decoration)
            recordname = experiment.recordname(node, decoration)
            if flatnames:
                write_a_record(output, flatten_hostname(recordname),
                               experiment.ipv4(node))
            else:
                write_a_record(output, sitename, experiment.ipv4(node))
                write_a_record(output, recordname, experiment.ipv4(node))


def export_experiment_records_v6(output,
                                 sites,
                                 experiment,
                                 decoration='',
                                 flatnames=False):
    comment(output, '%s v6%s%s' % (experiment.dnsname(), (
        ' decorated' if decoration else ''), (' flattened'
                                              if flatnames else '')))
    for site in sites:
        # TODO: change site['nodes'] to a pre-sorted list type.
        for node in sorted(site['nodes'].values(), key=lambda n: n.hostname()):
            # TODO: remove sitenames (or exclude mlab4's).
            if (node.ipv6_is_enabled() and experiment.ipv6(node)):
                sitename = experiment.sitename(node, decoration)
                recordname = experiment.recordname(node, decoration)
                if flatnames:
                    write_aaaa_record(output, flatten_hostname(recordname),
                                      experiment.ipv6(node))
                else:
                    write_aaaa_record(output, sitename, experiment.ipv6(node))
                    write_aaaa_record(output, recordname, experiment.ipv6(node))


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
                'city': '',
                'country': '',
                'latitude': None,
                'longitude': None
            }
        metro = [name, name[:-2]]
        sitestats.append({
            'site': name,
            'metro': metro,
            'city': location['city'],
            'country': location['country'],
            'latitude': location['latitude'],
            'longitude': location['longitude']
        })
    json.dump(sitestats, output)


def export_legacy(output, experiments, select_regex):
    """Exports json for legacy monitoring by Prometheus."""
    targets = []
    for experiment in experiments:
        # TODO(soltesz): change 'network_list' to a sorted list of node objects.
        for _, node in experiment['network_list']:
            if experiment['index'] is None:
                continue
            # TODO(soltesz): provide a template for formatting the hostname.
            hostname = '%s:9090' % experiment.hostname(node)
            if select_regex and not re.search(select_regex, hostname):
                continue
            targets.append(hostname)

    # TODO(soltesz): allow adding extra labels and an alternate service name.
    legacy = [{ "labels": {"service": "sidestream"}, "targets": targets}]
    json.dump(legacy, output, indent=4)


def export_mlab_host_ips(output, sites, experiments):
    """Writes csv data of all M-Lab servers and experiments to output."""
    # Export server names and addresses.
    for site in sites:
        # TODO(soltesz): change 'nodes' to be a sorted list of node objects.
        for _, node in site['nodes'].iteritems():
            output.write('{name},{ipv4},{ipv6}\n'.format(name=node.hostname(),
                                                         ipv4=node.ipv4(),
                                                         ipv6=node.ipv6()))

    # Export experiment names and addresses.
    for experiment in experiments:
        # TODO(soltesz): change 'network_list' to a sorted list of node objects.
        for _, node in experiment['network_list']:
            if experiment['index'] is None:
                continue
            output.write(
                '{name},{ipv4},{ipv6}\n'.format(name=experiment.hostname(node),
                                                ipv4=experiment.ipv4(node),
                                                ipv6=experiment.ipv6(node)))


# TODO(soltesz): this function is too specific to node network configuration.
# Replace this function with a more general interface for accessing
# configuration information for a site, node, slice, or otherwise.
def export_mlab_server_network_config(output, sites, name_tmpl, input_tmpl,
                                      select_regex):
    """Evaluates input_tmpl with values from the server network configuration.

    NOTE: Only fields returned by the model.Node.interface function are
    supported.

    If select_regex is not None, then only node hostnames that match the
    regular expression are processed.

    For every server, the input_tmpl is evaluated with the current server's
    network interface. The result is written to a new filename based on
    name_tmpl.

    Example:
        name_tmpl = "{{hostname}}.example"
        input_tmpl = "The IP address is {{ip}}"

        Will create files named like:
            mlab1.abc01.measurement-lab.org.example
            ...

        That contain:
            The IP address is 192.168.0.1

    Args:
        output: open file for writing, progress messages are written here.
        sites: list of model.Site, where all sites are processed.
        name_tmpl: str, the name of an output file as a template.
        input_tmpl: open file for reading, contains the template content.
        select_regex: str, a regular expression used to select node hostnames.

    Raises:
        IOError, could not create or write to a file.
    """
    template = BracketTemplate(input_tmpl.read())
    output_name = BracketTemplate(name_tmpl)
    for site in sites:
        for hostname, node in site['nodes'].iteritems():
            # TODO(soltesz): support multiple (or all) object types.
            if select_regex and not re.search(select_regex, hostname):
                continue
            i = node.interface()
            # Add 'hostname' so that it is available to templates.
            i['hostname'] = hostname
            filename = output_name.safe_substitute(i)
            with open(filename, 'w') as f:
                output.write("%s\n" % filename)
                f.write(template.safe_substitute(i))


def export_scraper_kubernetes_config(filename_template, experiments,
                                     contents_template):
    """Generates kubernetes deployment configs based on an input template."""
    filename_tmpl = BracketTemplate(filename_template)
    contents_tmpl = BracketTemplate(contents_template)
    configs = []
    for experiment in experiments:
        slice_name = experiment['name']
        for name, node in experiment['network_list']:
            node_name, site_name, _ = name.split('.', 2)
            if experiment['index'] is None:
                continue
            rsync_host = experiment.hostname(node)
            for rsync_module in experiment['rsync_modules']:
                config = {'site': site_name,
                          'node': node_name,
                          'experiment': slice_name}
                for k in config.keys():
                    # Kubernetes names must match the regex [a-zA-Z0-9.-]+
                    # Replace all sequences of characters that can't be part of
                    # a kubernetes name with a single dash.
                    config[k] = re.sub(r'[^a-zA-Z0-9.-]+', '-', config[k])
                # The rsync_module and rsync_host are only used as values, and
                # so do not need to be (and should not be) substituted as above.
                config['rsync_module'] = rsync_module
                config['rsync_host'] = rsync_host
                filename = filename_tmpl.safe_substitute(config)
                with open(filename, 'w') as config_file:
                    config_file.write(contents_tmpl.safe_substitute(config))


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
    elif options.format == 'server-network-config':
        with open(options.template) as template:
            export_mlab_server_network_config(
                sys.stdout, sites, options.filename, template, options.select)
    elif options.format == 'zone':
        with open(options.zoneheader, 'r') as header:
            if options.serial == 'auto':
                options.serial = serial_rfc1912(time.gmtime())
            export_mlab_zone_header(sys.stdout, header, options)
            sys.stdout.write("\n\n")
            export_mlab_zone_records(sys.stdout, sites, experiments)
    elif options.format == 'scraper_kubernetes':
        with open(options.template, 'r') as template:
            export_scraper_kubernetes_config(options.filename, experiments,
                                             template.read())
    elif options.format == 'legacy_prometheus':
        export_legacy(sys.stdout, experiments, options.select)
    else:
        logging.error('Sorry, unknown format: %s', options.format)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, IOError):
        pass
