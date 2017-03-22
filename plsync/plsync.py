#!/usr/bin/env python

import pprint
from planetlab import session
from planetlab import sync
import sys

def usage():
    return """
    plsync.py takes static configurations stored in sites.py and slices.py
        and applies them to the PLC database adding or updating objects, 
        tags, and other values when appropriate.

    Add a New Site:
        ./plsync.py --dryrun ....
                Only perform Get* api calls.  Absolutely no changes are made
                to the PLC DB. HIGHLY recommended before changes.

        ./plsync.py --syncsite nuq01 --allsteps
                Creating a new site requires admin permission.  First, edit
                sites.py to add details for nuq01. Next, run this command to
                create site, nodes, PCUs and configuration.

        ./plsync.py --syncslice all --on nuq01 --allsteps
                Use the standard set of slices defined in slices.py and add
                their configuration to the servers at site 'nuq01'.  Perform
                all configuration steps (i.e. add slice ips, and add
                whitelist).

    Download Boot image:
        ./plsync.py --syncsite nuq0t --getbootimages
                This command downloads boot images for a site to the PWD. By
                default, downloading boot images recreates the node key in the
                PLC db. For new site installs, this is safe. For running
                systems, this will cause reboot failures (due to auth failure
                with PLC) until the new boot images are deployed.

        ./plsync.py --syncsite nuq0t --on mlab1.nuq0t.measurement-lab.org \\
             --getbootimages --node-key-keep
                To preserve the node key and generate a new boot image use the
                --node-key-keep flag. This can optionally be used on a single
                machine.

    Add New Operator (rare):
        ./plsync.py --syncsite all --addusers
                Adding a new operator to all M-Lab sites requires admin
                permission.  Add the new operator email address to sites.py in
                the variable 'pi_list'.  Finally, run this command.  The
                operator account should already exist in the PlanetLab
                database, and after completion will have permission to act on
                M-Lab servers or PCUs at all M-Lab sites.

    Alternate Boot Server:
        ./plsync.py --url https://boot-test.measurementlab.net/PLCAPI/ ...
                The default API target for plsync is PlanetLab's PLCAPI server.
                To direct plsync to a different target use '--url <url>'

    Configure a Single Slice:
        ./plsync.py --syncslice <slicename> --allsteps
                Add the new slice specification to slices.py. Next, run this
                command.  By default, syncslice will apply to *all* sites. If
                you would like to limit the sites, specify "--on <sitename>'

                Also, useful to update slice attributes for a single slice.  For
                instance, to disable a slice prior to deletion from M-Lab, you
                could add the attribute 'enabled=0' to slices.py and run this
                command.  Or, to increase the disk quota. disk_max='80000000'

    Add IPv6 to Slice on a Single Server:
        ./plsync.py --syncslice iupui_ndt --allstesps \\
                    --on mlab1.nuq0t.measurement-lab.org --allsteps
                In slices.py update Slice() definition to include ipv6="all".
                Then, resync the slice configuration for a given hostname.
                This command is useful for staging updates, rather than
                applying them globally.

    Other Examples:
        ./plsync.py --syncslice all --on nuq01
                Associates all slices with machines at given site. Also, 
                updates global slice attributes.  Should only be run after 
                setting up the site with '--syncsite'

        ./plsync.py --syncsite all
                Syncs all sites. Verifies existing sites & slices, creates
                sites that do not exist.  This will take a very long time
                due to the delays for every RPC call to the PLC api.

                This command would be useful once migrating to a new
                boot-server.  This would populate the entire db based on the
                current configuration in sites.py & slices.py (which should be
                identical to PlanetLab's db).

    Future Notes:
        Since an external sites & slices list was necessary while M-Lab was
        part of PlanetLab to differentiate mlab from non-mlab, 
        it may be possible to eliminate sites.py and slices.py. That really only
        needs to run once and subsequent slice operations could query the DB
        for a list of current sites or hosts.  More intelligent update 
        functions could re-assign nodes to nodegroups, assign which hosts
        are in the ipv6 pool, etc. just a thought.

        Keeping slices.py as a concise description of what and how slices
        are deployed to M-Lab is probably still helpful to see everything in
        one place.  But, this could be saved in the form of a list of commands
        to plsync.py with explicit arguments for the values currently
        contained in slices.py.  This would make plsync.py just another
        command line tool and separate config from function more clearly.
"""

def main():

    from optparse import OptionParser
    parser = OptionParser(usage=usage())

    parser.add_option("", "--dryrun", dest="debug", action="store_true",
                default=False,
                help="only issues 'Get*' calls to the API. Commits nothing.")
    parser.add_option("", "--verbose", dest="verbose", action="store_true",
                default=False,
                help="print all the PLC API calls being made.")
    parser.add_option("", "--url", dest="url", 
                default=session.API_URL,
                help="PLC url to contact")
    parser.add_option("", "--plcconfig", dest="plcconfig",
                default=session.PLC_CONFIG,
                help="path to file containing plc login information.")

    parser.add_option("", "--on", metavar="hostname", dest="ondest", 
                default=None,
                help="only act on the given hostname (or sitename)")

    parser.add_option("", "--syncsite", metavar="site", dest="syncsite", 
                default=None,
                help="sync the given site, nodes, and pcus. Can be 'all'")
    parser.add_option("", "--syncslice", metavar="slice", dest="syncslice", 
                default=None,
                help="sync the given slice and its attributes. Can be 'all'")

    parser.add_option("-A", "--allsteps", dest="allsteps",
                action="store_true",
                default=False,
                help="perform all the following 'add' steps (in context)")
    parser.add_option("", "--addnodes", dest="addnodes",
                action="store_true",
                default=False,
                help=("[syncsite] create nodes during site sync"))
    parser.add_option("", "--addinterfaces", dest="addinterfaces",
                action="store_true",
                default=False,
                help=("[syncsite] create/update ipv4 Interfaces. Omitting "+
                      "this option only syncs ipv6 configuration (which is "+
                      "treated differently in the DB)") )
    parser.add_option("", "--addusers", dest="addusers",
                action="store_true",
                default=False,
                help=("[syncsite] add PIs to sites"))
    parser.add_option("", "--createusers", action="store_true",
                dest="createusers",
                default=False,
                help=("normally, users are assumed to exist. This option "+
                      "creates them first and gives them a default password. "+
                      "Useful for testing. Users are not assigned to slices."))

    parser.add_option("", "--addwhitelist", dest="addwhitelist",
                action="store_true",
                default=False,
                help=("[syncslice] add the given slice to whitelists."))
    parser.add_option("", "--addsliceips", dest="addsliceips",
                default=False,
                action="store_true",
                help="[syncslice] assign IPs (v4 and/or v6) to slices")

    parser.add_option("", "--createslice", action="store_true",
                dest="createslice",
                default=False,
                help=("normally, slices are assumed to exist. This option "+
                      "creates them first. Useful for testing. Users are not "+
                      "assigned to new slices."))
    parser.add_option("", "--getbootimages", dest="getbootimages",
                action="store_true",
                default=False,
                help=("download the ISO boot images for nodes. Without the "
                      "--node-key-keep flag, this is a destructive operation."))
    parser.add_option("", "--node-key-keep", dest="nodekeykeep",
                action="store_true",
                default=False,
                help=("When downloading an ISO boot image, preserve the node "
                      "key generated by previous downloads. This flag enables "
                      "an operator to generate multiple ISOs for hardware "
                      "updates without breaking the current deployment."))

    parser.add_option("", "--sitesname", metavar="sites", dest="sitesname",
                default="sites",
                help="the name of the module with Site() definitions")
    parser.add_option("", "--slicesname", metavar="slices", dest="slicesname",
                default="slices",
                help="the name of the module with Slice() definitions")

    parser.add_option("", "--sitelist", metavar="site_list", dest="sitelist",
                default="site_list",
                help="the site list variable name.")
    parser.add_option("", "--slicelist", metavar="slice_list", dest="slicelist",
                default="slice_list",
                help="the slice list variable name.")

    (options, args) = parser.parse_args()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    # NOTE: if allsteps is given, set all steps to True
    if options.allsteps:
        options.addwhitelist=True
        options.addsliceips=True
        options.addinterfaces=True
        options.addnodes=True
        options.addusers=True

    site_list =  getattr(__import__(options.sitesname), options.sitelist)
    slice_list =  getattr(__import__(options.slicesname), options.slicelist)

    print "setup plc session"
    session.setup_global_session(options.url, options.debug, options.verbose,
                                 options.plcconfig)

    # always setup the configuration for everything (very fast)
    print "loading slice & site configuration"
    for sslice in slice_list:
        for site in site_list:
            for host in site['nodes']:
                h = site['nodes'][host]
                sslice.add_node_address(h)

    # begin processing arguments to apply filters, etc
    if options.syncsite is not None and options.syncslice is None:
        print "sync site"
        for site in site_list: 
            # sync everything when syncsite is None, 
            # or only when it matches
            if (options.syncsite == "all" or 
                options.syncsite == site['name']):
                print "Syncing: site", site['name']
                sync.SyncSite(site, options.ondest, options.addusers,
                              options.addnodes, options.addinterfaces,
                              options.getbootimages, options.createusers,
                              options.nodekeykeep)

    elif options.syncslice is not None and options.syncsite is None:
        print options.syncslice
        for sslice in slice_list: 
            if (options.syncslice == "all" or 
                options.syncslice == sslice['name']):
                print "Syncing: slice", sslice['name']
                sync.SyncSlice(sslice, options.ondest, options.addwhitelist,
                               options.addsliceips, options.addusers,
                               options.createslice)

    else:
        print usage()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
