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

    # TODO(#116): Delete this class and local definition of safe_substitute once
    # the resolution for http://bugs.python.org/issue17078 is in all
    # contemporary python packages.
    class _multimap:
        """Helper class for combining multiple mappings.

        Used by .{safe_,}substitute() to combine the mapping and keyword
        arguments.
        """
        def __init__(self, primary, secondary):
            self._primary = primary
            self._secondary = secondary

        def __getitem__(self, key):
            try:
                return self._primary[key]
            except KeyError:
                return self._secondary[key]

    def safe_substitute(self, *args, **kws):
        if len(args) > 1:
            raise TypeError('Too many positional arguments')
        if not args:
            mapping = kws
        elif kws:
            mapping = _multimap(kws, args[0])
        else:
            mapping = args[0]
        # Helper function for .sub()
        def convert(mo):
            named = mo.group('named') or mo.group('braced')
            if named is not None:
                try:
                    # We use this idiom instead of str() because the latter
                    # will fail if val is a Unicode containing non-ASCII
                    return '%s' % (mapping[named],)
                except KeyError:
                    return mo.group()
            if mo.group('escaped') is not None:
                return self.delimiter
            if mo.group('invalid') is not None:
                return mo.group()
            raise ValueError('Unrecognized named group in pattern',
                             self.pattern)
        return self.pattern.sub(convert, self.template)


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

    mlabconfig.py --format=prom-targets \
        --template_target={{hostname}}:9090 \
        --label service=sidestream \
        --select="npad.iupui.*lga0t.*"

    mlabconfig.py --format=prom-targets \
        --template_target={{hostname}}:7999 \
        --label module=rsyncd_online \
        --label service=rsyncd \
        --rsync \
        --select=".*lga0t.*"

    mlabconfig.py --format=prom-targets-nodes \
        --template_target={{hostname}}:806 \
        --label module=ssh_v4_online \
        --label service=machine_online \
        --select=".*lga0t.*"

    mlabconfig.py --format=prom-targets-sites \
        --template_target=s1.{{sitename}}.measurement-lab.org \
        --label service=snmp \
        --label __exporter_project=sandbox
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
        '--template_target',
        dest='template_target',
        action='append',
        default=[],
        help=('Target is interpreted as a template used to format blackbox '
              'targets.'))
    parser.add_option(
        '',
        '--label',
        dest='labels',
        action='append',
        default=[],
        help='Adds key/value labels to a resulting prometheus targets file.')
    parser.add_option(
        '',
        '--rsync',
        dest='rsync',
        action='store_true',
        default=False,
        help='Only process experiments that have rsync modules defined.')
    parser.add_option(
        '',
        '--use_flatnames',
        dest='use_flatnames',
        action='store_true',
        default=False,
        help='Whether to return TLS-formatted host names (dashes, not dots.)')
    parser.add_option(
        '',
        '--decoration',
        dest='decoration',
        default='',
        choices=['', 'v4', 'v6'],
        help='Protocol decoration for Prom targets (e.g, mlab1v4.abc01).')
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

    # If labels are given, parse them and check for malformed values.
    if options.labels:
        new_labels = {}
        for label in options.labels:
            fields = label.split('=')
            if len(fields) != 2:
                logging.error(
                    'Invalid "--label %s"; use "--label key=value" format.',
                    label)
                sys.exit(1)
            # Save the key/value.
            new_labels[fields[0]] = fields[1]
        # Update the value of options.labels (and change the type to a dict).
        options.labels = new_labels

    # If we're generating prometheus service discovery files, require labels.
    if options.format in ['prom-targets', 'prom-targets-nodes']:
        if not options.labels:
            logging.error(
                'Provide at least one --label for "%s" format', options.format)
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


def export_mlab_site_stats(sites):
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
            'longitude': location['longitude'],
            'roundrobin': site.get('roundrobin', False)
        })

    return sitestats


def export_mlab_host_ips(sites, experiments):
    """Writes csv data of all M-Lab servers and experiments to output."""
    output = StringIO.StringIO()
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

    return output


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
                                     contents_template, select):
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
            if select and not re.search(select, rsync_host):
                continue
            for rsync_module in experiment['rsync_modules']:
                config = {'machine': node.hostname(),
                          'site': site_name,
                          'node': node_name,
                          'experiment': experiment.dnsname(),
                          'rsync_module': rsync_module,
                          'rsync_host': rsync_host}
                for key, value in list(config.items()):
                    # Kubernetes names must match the regex [a-zA-Z0-9.-]+
                    # Replace all sequences of characters that aren't a letter
                    # or number with a single dash to make the strings safe.
                    config[key + '_safe'] = re.sub(r'[^a-zA-Z0-9]+', '-',
                                                   value)
                filename = filename_tmpl.safe_substitute(config)
                with open(filename, 'w') as config_file:
                    config_file.write(contents_tmpl.safe_substitute(config))


def select_prometheus_experiment_targets(experiments, select_regex,
                                         target_templates, common_labels,
                                         rsync_only, use_flatnames,
                                         decoration):
    """Selects and formats targets from experiments.

    Args:
      experiments: list of planetlab.Slice objects, used to enumerate hostnames.
      select_regex: str, a regex used to choose a subset of hostnames. Ignored
          if empty.
      target_templates: list of templates for formatting the target(s) from the
          hostname. e.g. {{hostname}}:7999, https://{{hostname}}/some/path
      common_labels: dict of str, a set of labels to apply to all targets.
      rsync_only: bool, skip experiments without rsync_modules.
      use_flatnames: bool, return "flattened" hostnames suitable for TLS/SSL
          wildcard certificates.
      decoration: str, return protocol 'decorated' host names
          (e.g., mlab1v6.abc01).

    Returns:
      list of dict, each element is a dict with 'labels' (a dict of key/values)
          and 'targets' (a list of targets).
    """
    records = []
    for experiment in experiments:
        for _, node in experiment['network_list']:
            # Skip experiments without an IP index.
            if experiment['index'] is None:
                continue

            labels = common_labels.copy()
            labels['experiment'] = experiment.dnsname()
            labels['machine'] = node.hostname()

            host = experiment.hostname(node, decoration)

            # Don't use the flatten_hostname() function in this module because
            # it adds too much overhead. Just replace the first three dots with
            # dashes.
            if use_flatnames:
                host = host.replace('.', '-', 3)
            # Consider all experiments or only those with rsync modules.
            if not rsync_only or experiment['rsync_modules']:
                if select_regex and not re.search(select_regex, host):
                    continue
                targets = []
                for tmpl in target_templates:
                    target_tmpl = BracketTemplate(tmpl)
                    target = target_tmpl.safe_substitute({'hostname': host})
                    targets.append(target)
                records.append({
                    'labels': labels,
                    'targets': targets,
                })
    return records


def select_prometheus_node_targets(sites, select_regex, target_templates,
                                   common_labels, decoration):
    """Selects and formats targets from site nodes.

    Args:
      sites: list of planetlab.Site objects, used to generate hostnames.
      select_regex: str, a regex used to choose a subset of hostnames. Ignored
          if empty.
      target_templates: list of templates for formatting the target(s) from the
          hostname. e.g. {{hostname}}:7999, https://{{hostname}}/some/path
      common_labels: dict of str, a set of labels to apply to all targets.
      decoration: str, used to "decorate" the hostname with a protocol
          (e.g., mlab1v6.abc01).

    Returns:
      list of dict, each element is a dict with 'labels' (a dict of key/values)
          and 'targets' (a list of targets).
    """
    records = []
    for site in sites:
        for _, node in site['nodes'].iteritems():
            if select_regex and not re.search(select_regex, node.hostname()):
                continue
            labels = common_labels.copy()
            labels['machine'] = node.hostname()
            targets = []

            host = node.hostname(decoration)

            for tmpl in target_templates:
                target_tmpl = BracketTemplate(tmpl)
                target = target_tmpl.safe_substitute({'hostname': host})
                targets.append(target)
            records.append({
                'labels': labels,
                'targets': targets,
            })
    return records


def select_prometheus_site_targets(sites, select_regex, target_templates,
                                   common_labels):
    """Selects and formats site targets.

    Args:
      sites: list of planetlab.Site objects, used to generate site names.
      select_regex: str, a regex used to choose a subset of hostnames. Ignored
          if empty.
      target_templates: list of templates for formatting the target(s) from the
          hostname. e.g. s1.{{sitename}}.measurement-lab.org:9116
      common_labels: dict of str, a set of labels to apply to all targets.

    Returns:
      list of dict, each element is a dict with 'labels' (a dict of key/values)
          and 'targets' (a list of targets).
    """
    records = []
    for site in sites:
        if select_regex and not re.search(select_regex, site['name']):
            continue
        labels = common_labels.copy()
        labels['site'] = site['name']
        targets = []
        for tmpl in target_templates:
            target_tmpl = BracketTemplate(tmpl)
            target = target_tmpl.safe_substitute({'sitename': site['name']})
            targets.append(target)
        records.append({
            'labels': labels,
            'targets': targets,
        })
    return records


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
        output = export_mlab_host_ips(sites, experiments)
        sys.stdout.write(output.getvalue())
        # Temporary workaround for HND01 load issues. Remove or generalize:
        # https://github.com/m-lab/operator/issues/154
        sys.stdout.write(
            'mlab1.tyo01.measurement-lab.org,35.200.102.226,\n'
            'ndt.iupui.mlab1.tyo01.measurement-lab.org,35.200.102.226,\n'
            'mlab1.tyo02.measurement-lab.org,35.200.34.149,\n'
            'ndt.iupui.mlab1.tyo02.measurement-lab.org,35.200.34.149,\n'
            'mlab1.tyo03.measurement-lab.org,35.200.112.17,\n'
            'ndt.iupui.mlab1.tyo03.measurement-lab.org,35.200.112.17,\n'
        )

    elif options.format == 'sitestats':
        sitestats = export_mlab_site_stats(sites)

        # Temporary workaround for HND01 load issues. Remove or generalize:
        # https://github.com/m-lab/operator/issues/154
        for tyo in ['tyo01', 'tyo02', 'tyo03']:
            sitestats.append({
                'site': tyo,
                'metro': [tyo, tyo[:-2]],
                'city': 'Tokyo',
                'country': 'JP',
                'latitude': 35.552200,
                'longitude': 139.780000,
                'roundrobin': False
            })

        json.dump(sitestats, sys.stdout)

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
                                             template.read(), options.select)

    elif options.format == 'prom-targets':
        records = select_prometheus_experiment_targets(
            experiments, options.select, options.template_target,
            options.labels, options.rsync, options.use_flatnames,
            options.decoration)
        json.dump(records, sys.stdout, indent=4)

    elif options.format == 'prom-targets-nodes':
        records = select_prometheus_node_targets(
            sites, options.select, options.template_target, options.labels,
            options.decoration)
        json.dump(records, sys.stdout, indent=4)

    elif options.format == 'prom-targets-sites':
        records = select_prometheus_site_targets(
            sites, options.select, options.template_target, options.labels)
        json.dump(records, sys.stdout, indent=4)

    else:
        logging.error('Sorry, unknown format: %s', options.format)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, IOError):
        pass
