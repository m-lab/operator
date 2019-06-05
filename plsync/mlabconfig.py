#!/usr/bin/env python

import json
import logging
import optparse
import re
import string
import sys
import urllib2

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
            mapping = BracketTemplate._multimap(kws, args[0])
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
    mlabconfig.py --format=server-network-config  \
        --template_input=file.template \
        --template_output="$PATH/file-{{hostname}}.xyz" \
        --select=".*iad1t.*"
      (e.g. stage1-$HOSTNAME.ipxe)

    mlabconfig.py --format=prom-targets \
        --template_target={{hostname}}:9090 \
        --label service=sidestream \
        --select="npad.iupui.*lga0t.*"

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
    parser.set_defaults(force=False)

    parser.add_option(
        '',
        '--sites',
        metavar='sites',
        dest='sites',
        default='https://siteinfo.mlab-sandbox.measurementlab.net/v1/sites/sites.json',
        help='The URL of sites configuration.')
    parser.add_option('',
                      '--format',
                      metavar='format',
                      dest='format',
                      default='',
                      help='Format of output.')
    parser.add_option(
        '',
        '--template_input',
        dest='template_input',
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
    parser.add_option(
        '',
        '--physical',
        dest='physical',
        action='store_true',
        default=False,
        help='Only process physical sites.')

    (options, args) = parser.parse_args()

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


# TODO(soltesz): this function is too specific to node network configuration.
# Replace this function with a more general interface for accessing
# configuration information for a site, node, slice, or otherwise.
def export_mlab_server_network_config(output, sites, name_tmpl, input_tmpl,
                                      select_regex, labels, only_physical):
    """Evaluates input_tmpl with values from the server network configuration.

    NOTE: Only fields returned by the model.Node.interface function and any
    key/values in labels are supported.

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
        sites: list of siteinfo site objects, used to enumerate nodes.
        name_tmpl: str, the name of an output file as a template.
        input_tmpl: open file for reading, contains the template content.
        select_regex: str, a regular expression used to select node hostnames.
        labels: dict, extra key values available in the templates.
        only_physical: bool, whether to restrict targets to physical sites.

    Raises:
        IOError, could not create or write to a file.
    """
    template = BracketTemplate(input_tmpl.read())
    output_name = BracketTemplate(name_tmpl)
    for site in sites:
        if only_physical and site['annotations']['type'] != 'physical':
            continue
        for node in site['nodes']:
            # TODO(soltesz): support multiple (or all) object types.
            if select_regex and not re.search(select_regex, node['hostname']):
                continue
            # Add 'hostname' so that it is available to templates.
            i = {'hostname': node['hostname']}
            # Get IPv4 settings.
            i.update({'ipv4_' + k: node['v4'][k] for k in node['v4']})
            i['ipv4_enabled'] = 'true' if node['v4']['ip'] else 'false'
            i['ipv4_address'] = i['ipv4_ip']
            # Add IPv6 settings.
            i.update({'ipv6_' + k: node['v6'][k] for k in node['v6']})
            i['ipv6_enabled'] = 'true' if node['v6']['ip'] else 'false'
            i['ipv6_address'] = i['ipv6_ip']
            # Add extra provided labels.
            i.update(labels)
            filename = output_name.safe_substitute(i)
            with open(filename, 'w') as f:
                output.write("%s\n" % filename)
                f.write(template.safe_substitute(i))


def select_prometheus_experiment_targets(sites, select_regex,
                                         target_templates, common_labels,
                                         rsync_only, use_flatnames,
                                         decoration, only_physical):
    """Selects and formats targets from experiments.

    Args:
      sites: list of siteinfo site objects, used to enumerate experiments.
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
      only_physical: bool, whether to restrict targets to physical sites.

    Returns:
      list of dict, each element is a dict with 'labels' (a dict of key/values)
          and 'targets' (a list of targets).
    """
    records = []
    for site in sites:
        if only_physical and site['annotations']['type'] != 'physical':
            continue
        for node in site['nodes']:
            for experiment in node['experiments']:
                labels = common_labels.copy()
                labels['experiment'] = experiment['name']
                labels['machine'] = node['hostname']

                # Skip if rsync_only is true but the experiment has no modules.
                if rsync_only and not experiment['rsync_modules']:
                    continue

                # Skip if the given regex doesn't match the experiment hostname.
                if select_regex and \
                    not re.search(select_regex, experiment['hostname']):
                    continue

                # Add decoration, if needed.
                prefix = experiment['hostname'][:len(experiment['name'])+6]
                suffix = experiment['hostname'][len(experiment['name'])+6:]
                hostname = prefix + decoration + suffix

                if use_flatnames:
                    hostname = hostname.replace('.', '-', 3)

                targets = []
                for tmpl in target_templates:
                    target_tmpl = BracketTemplate(tmpl)
                    target = target_tmpl.safe_substitute({'hostname': hostname})
                    targets.append(target)
                records.append({
                    'labels': labels,
                    'targets': targets,
                })
    return records


def select_prometheus_node_targets(sites, select_regex, target_templates,
                                   common_labels, decoration, only_physical):
    """Selects and formats targets from site nodes.

    Args:
      sites: list of siteinfo site objects, used to enumerate nodes.
      select_regex: str, a regex used to choose a subset of hostnames. Ignored
          if empty.
      target_templates: list of templates for formatting the target(s) from the
          hostname. e.g. {{hostname}}:7999, https://{{hostname}}/some/path
      common_labels: dict of str, a set of labels to apply to all targets.
      decoration: str, used to "decorate" the hostname with a protocol
          (e.g., mlab1v6.abc01).
      only_physical: bool, whether to restrict targets to physical sites.

    Returns:
      list of dict, each element is a dict with 'labels' (a dict of key/values)
          and 'targets' (a list of targets).
    """
    records = []
    for site in sites:
        if only_physical and site['annotations']['type'] != 'physical':
            continue
        for node in site['nodes']:
            if select_regex and not re.search(select_regex, node['hostname']):
                continue
            labels = common_labels.copy()
            labels['machine'] = node['hostname']
            targets = []

            prefix = node['hostname'][:5]
            suffix = node['hostname'][5:]
            hostname = prefix + decoration + suffix

            for tmpl in target_templates:
                target_tmpl = BracketTemplate(tmpl)
                target = target_tmpl.safe_substitute({'hostname': hostname})
                targets.append(target)
            records.append({
                'labels': labels,
                'targets': targets,
            })
    return records


def select_prometheus_site_targets(sites, select_regex, target_templates,
                                   common_labels, only_physical):
    """Selects and formats site targets.

    Args:
      sites: list of siteinfo site objects, used to enumerate nodes.
      select_regex: str, a regex used to choose a subset of hostnames. Ignored
          if empty.
      target_templates: list of templates for formatting the target(s) from the
          hostname. e.g. s1.{{sitename}}.measurement-lab.org:9116
      common_labels: dict of str, a set of labels to apply to all targets.
      only_physical: bool, whether to restrict targets to physical sites.

    Returns:
      list of dict, each element is a dict with 'labels' (a dict of key/values)
          and 'targets' (a list of targets).
    """
    records = []
    for site in sites:
        if select_regex and not re.search(select_regex, site['name']):
            continue
        if only_physical and site['annotations']['type'] != 'physical':
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
    (options, _) = parse_flags()

    sites = json.loads(urllib2.urlopen(options.sites).read())

    if options.format == 'server-network-config':
        with open(options.template_input) as template:
            export_mlab_server_network_config(
                sys.stdout, sites, options.filename, template, options.select,
                options.labels, options.physical)

    elif options.format == 'prom-targets':
        records = select_prometheus_experiment_targets(
            sites, options.select, options.template_target,
            options.labels, options.rsync, options.use_flatnames,
            options.decoration, options.physical)
        json.dump(records, sys.stdout, indent=4)

    elif options.format == 'prom-targets-nodes':
        records = select_prometheus_node_targets(
            sites, options.select, options.template_target, options.labels,
            options.decoration, options.physical)
        json.dump(records, sys.stdout, indent=4)

    elif options.format == 'prom-targets-sites':
        records = select_prometheus_site_targets(
            sites, options.select, options.template_target, options.labels,
            options.physical)
        json.dump(records, sys.stdout, indent=4)

    else:
        logging.error('Sorry, unknown format: %s', options.format)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, IOError):
        pass
