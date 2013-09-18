#!/usr/bin/env python

import pprint
from planetlab import session
import sys

def usage():
    return """
    plsync.py takes static configurations stored in sites.py and slices.py
        and applies them to the PLC database adding or updating objects, 
        tags, and other values when appropriate.

    TODO:
        Implement common operations:

        ./plsync.py --syncsite xyz --getbootimages 
                This would setup the basic networking, and download boot images.
                Subsequent calls should assume these are done already.

    Examples:
        ./plsync.py --dryrun ....
                Only perform Get* api calls.  Absolutely no changes are made
                to the PLC DB. HIGHLY recommended before changes.

        ./plsync.py --syncsite nuq01
                Creates site, nodes, and pcus for the given site name.

        ./plsync.py --syncslice <slicename> --skipsliceips --skipwhitelist
                Useful for updating a slice attributes for a single slice.  For
                instance, to disable a slice prior to deletion from M-Lab, you
                could add the attribute 'enabled=0' to slices.py and run this
                command.

        ./plsync.py --syncslice all --on nuq01
                Associates all slices with machines at given site. Also, 
                updates global slice attributes.  Should only be run after 
                setting up the site with '--syncsite'

        ./plsync.py --syncsite all
                Syncs all sites. Verifies existing sites & slices, creates
                sites that do not exist.  This will take a very long time
                due to the delays for every RPC call to the PLC api.

        ./plsync.py --syncsite nuq01 --on mlab4.nuq01.measurement-lab.org
                Resync the node configuration for given hostname.

        ./plsync.py --syncslice ooni_probe --skipwhitelist
                Like "--syncslice all" except only applied to the given
                slicename.  --skipwhitelist assumes that the slice was
                previously whitelisted, so doing it again is unnecessary.

        ./plsync.py --syncslice ooni_probe --on mlab4.nuq01.measurement-lab.org
                Performs the --syncslice operations, but only on the given
                target machine.  This is useful for applying IPv6 address
                updates (or other slice attributes) to only a few machines, 
                instead of all of them.  Global slice attributes will also be 
                applied, despite "--on <hostname>".

                In this example, ooni_probe must be explicitly permitted to
                receive an ipv6 on mlab4.nuq01 in slices.py. 
    Comments:
        Since an external sites & slices list was necessary while M-Lab was
        part of PlanetLab to differentiate mlab from non-mlab, 
        it may be possible to eliminate sites.py now. That really only
        needs to run once and subsequent slice operations could query the DB
        for a list of current sites or hosts.  More intelligent update 
        functions could to re-assign nodes to nodegroups, assign which hosts 
        are in the ipv6 pool, etc. just a thought.

        Keeping slices.py as a concise description of what and how slices
        are deployed to M-Lab is probably still helpful to see everything in
        one place.
"""

def main():

    from optparse import OptionParser
    parser = OptionParser(usage=usage())

    parser.set_defaults(syncsite=None, syncslice=None,
                        ondest=None, skipwhitelist=False, 
                        sitesname="sites",
                        slicesname="slices",
                        sitelist="site_list",
                        slicelist="slice_list",
                        skipsliceips=False, 
                        skipinterfaces=False,
                        skipnodes=False,
                        createslice=False,
                        getbootimages=False,
                        url=session.API_URL, debug=False, verbose=False, )

    parser.add_option("", "--dryrun", dest="debug", action="store_true",
                        help=("Only issues 'Get*' calls to the API.  "+
                              "Commits nothing to the API"))
    parser.add_option("", "--verbose", dest="verbose", action="store_true",
                        help="Print all the PLC API calls being made.")
    parser.add_option("", "--url", dest="url", 
                        help="PLC url to contact")

    parser.add_option("", "--on", metavar="hostname", dest="ondest", 
                        help="only act on the given host")

    parser.add_option("", "--syncsite", metavar="site", dest="syncsite", 
                help="only sync sites, nodes, pcus, if needed. (saves time)")
    parser.add_option("", "--syncslice", metavar="slice", dest="syncslice", 
                help="only sync slices and attributes of slices. (saves time)")

    parser.add_option("", "--skipwhitelist", dest="skipwhitelist", 
                action="store_true", 
                help=("dont try to white list the given slice. (saves time)"))
    parser.add_option("", "--skipsliceips", dest="skipsliceips", 
                action="store_true",
                help="dont try to assign ips to slice. (saves time)")
    parser.add_option("", "--skipinterfaces", dest="skipinterfaces", 
                action="store_true",
                help=("dont try to create new Interfaces or update existing "+
                      "Interfaces. This permits IPv6 maniuplation without "+
                      "changing legacy IPv4 configuration in DB.") )
    parser.add_option("", "--skipnodes", dest="skipnodes",
                action="store_true",
                help=("dont create nodes during site sync (saves time)"))
    parser.add_option("", "--createslice", action="store_true",
                dest="createslice",
                help=("Normally, slices are assumed to exist. This option "+
                      "creates them first. Useful for testing."))
    parser.add_option("", "--getbootimages", dest="getbootimages", 
                action="store_true",
                help=("Download the ISO boot images for Nodes. This is a"+
                      " destructive operation if ISOs have previously been "+
                      "downloaded."))

    parser.add_option("", "--sitesname", metavar="sites", dest="sitesname", 
                help="The name of the module with Site() definitions")
    parser.add_option("", "--slicesname", metavar="slices", dest="slicesname", 
                help="The name of the module with Slice() definitions")

    parser.add_option("", "--sitelist", metavar="site_list", dest="sitelist", 
                help="The site list variable name.")
    parser.add_option("", "--slicelist", metavar="slice_list", dest="slicelist", 
                help="The slice list variable name.")

    (options, args) = parser.parse_args()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    site_list =  getattr(__import__(options.sitesname), options.sitelist)
    slice_list =  getattr(__import__(options.slicesname), options.slicelist)

    print "setup plc session"
    session.setup_global_session(options.url, options.debug, options.verbose)

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
                site.sync(options.ondest, options.skipnodes,
                          options.skipinterfaces, options.getbootimages)

    elif options.syncslice is not None and options.syncsite is None:
        print options.syncslice
        for sslice in slice_list: 
            if (options.syncslice == "all" or 
                options.syncslice == sslice['name']):
                print "Syncing: slice", sslice['name']
                sslice.sync(options.ondest, 
                           options.skipwhitelist, 
                           options.skipsliceips,
                           options.createslice)

    else:
        print usage()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
