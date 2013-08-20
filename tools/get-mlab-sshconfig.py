#!/usr/bin/env python

import getpass
import xmlrpclib
import os
import sys
import re

SESSION_DIR=os.environ['HOME'] + "/.ssh"
SESSION_FILE=SESSION_DIR + "/ssh_mlab_session"
API_URL = "https://boot.planet-lab.org/PLCAPI/"
VERBOSE=False
DEBUG=False
SEVEN_DAYS=60*60*24*7

class API:
    """ API is a wrapper class around the PlanetLab API's xmlrpc calls.
        API() takes an auth struct and url, and automatically passes the auth
        struct to all calls.
    """
    def __init__(self, auth, url):
        self.auth = auth
        self.api = xmlrpclib.Server(url, verbose=False, allow_none=True)
    def __repr__(self):
        return self.api.__repr__()
    def __getattr__(self, name):
        method = getattr(self.api, name)
        if method is None:
            raise AssertionError("method does not exist")
        def call_method(aut, *params):
            if VERBOSE:
                print "%s(%s)" % (name, params)
            if DEBUG and "Update" in name:
                return -1
            else:
                return method(aut, *params)
        return lambda *params : call_method(self.auth, *params)

def refreshsession():
    # Either read session from disk or create it and save it for later
    print "PLC Username: ",
    sys.stdout.flush()
    username = sys.stdin.readline().strip()
    password = getpass.getpass("PLC Password: ")
    auth = {'Username' : username,
            'AuthMethod' : 'password',
            'AuthString' : password}
    plc = API(auth, API_URL)
    session = plc.GetSession(SEVEN_DAYS)
    try:
        os.makedirs(SESSION_DIR)
    except:
        pass
    f = open(SESSION_FILE, 'w')
    print >>f, session
    f.close()

def getapi():
    api = xmlrpclib.ServerProxy(API_URL, allow_none=True)
    auth = None
    authorized = False
    while not authorized:
        try:
            auth = {}
            auth['AuthMethod'] = 'session'
            auth['session'] = open(SESSION_FILE, 'r').read().strip()
            authorized = api.AuthCheck(auth)
            if not authorized:
                print "Refreshing your PLC session file: %s" % SESSION_FILE
                sys.stdout.flush()
                refreshsession()
        except:
            print "Need to setup a new PLC session file: %s" % SESSION_FILE
            sys.stdout.flush()
            refreshsession()

    assert auth is not None
    return API(auth, API_URL)

def get_mlabhosts(api, options):
    """ Makes necessary calls to collect all nodes, ssh keys associated
        with the ndoes, their IPv4 addresses and any IPv6 address.

        Args:
            api     - an API() object
            options - the options object returned after
                      OptionParser().parse_args()
        Returns:
            A dict that maps:
                hostname -> (ipv4 address, ipv6 address, ssh key)
            Either address may be None, but not both.
            The ssh key is guaranteed not to be None.
    """
    # NOTE: fetch hosts whose ssh_rsa_key value is not None.
    nodes = api.GetNodes({'hostname' : options.hostpattern,
                          '~ssh_rsa_key' : None},
                         ['hostname', 'node_id', 'ssh_rsa_key'])
    node_ids = [ n['node_id'] for n in nodes ]

    # NOTE: get all interfaces for the above node_ids
    ifs = api.GetInterfaces({'is_primary' : True, 'node_id' : node_ids},
                            ['ip', 'node_id', 'interface_id'])
    if_ids = [ i['interface_id'] for i in ifs ]

    # NOTE: ipv6 addrs are tags on the primary interfaces above.
    # NOTE: so, get all interface tags for the above interface_ids.
    iftags = api.GetInterfaceTags({'tagname' : 'ipv6addr',
                                   'interface_id' : if_ids},
                                  ['value', 'interface_id'])

    # NOTE: now associate interface_id to node_id and ipv6 address
    if_id2node_id = { i['interface_id']:i['node_id'] for i in ifs }
    if_id2ipv6    = { it['interface_id']:it['value'] for it in iftags }

    node_id2name = { n['node_id']:n['hostname'] for n in nodes }
    node_id2key  = { i['node_id']:i['ssh_rsa_key'] for i in nodes }
    node_id2ipv4 = { i['node_id']:i['ip'] for i in ifs }
    # NOTE: so finally, we can map node_id to ipv6 address.
    #       Not all ipv4 interfaces have ipv6 addrs.
    #       But all interfaces in if_id2ipv6 do.
    node_id2ipv6 = { if_id2node_id[if_id]:if_id2ipv6[if_id]
                     for if_id in if_id2ipv6.keys() }

    # NOTE: now pull all these values into a single dict.
    host2v4v6key = {}
    for node_id in node_id2name:
        hostname = node_id2name[node_id]
        ipv4=None
        if node_id in node_id2ipv4:
            ipv4 = node_id2ipv4[node_id]
        ipv6=None
        if node_id in node_id2ipv6:
            ipv6 = node_id2ipv6[node_id]
        key=None
        if node_id in node_id2key:
            key = node_id2key[node_id]
        # GetNodes() should only return non-None keys.
        assert (key is not None) 
        host2v4v6key[hostname] = (ipv4,ipv6,key)

    return host2v4v6key

def has_write_access(filename):
    if os.path.exists(filename):
        return os.access(filename, os.W_OK)
    else:
        # NOTE: if the file doesn't exist make sure we can write to directory.
        return os.access(os.path.dirname(filename), os.W_OK)

def get_knownhosts(hosts_file):
    """ Reads the content of hosts_file as if it were a known_hosts file.
        Args:
            hosts_file - filename
        Returns:
            Tuple with (hosts_lines as list, file content as string)
    """
    # collect all entries currently in known_hosts_mlab and ssh config
    if os.path.exists(hosts_file):
        if not os.access(hosts_file, os.R_OK):
            print "Error: we cannot read to %s" % hosts_file
            sys.exit(1)
        hosts_fd = open(hosts_file, 'r')
        hosts_lines = [ line.strip() for line in hosts_fd.readlines() ]
        hosts_fd.seek(0)
        hosts_blob = hosts_fd.read()
        hosts_fd.close()
    else:
        # NOTE: file doesn't exist yet, no big deal.
        hosts_lines = [ ]
        hosts_blob = ""

    if not has_write_access(hosts_file):
        print "Error: we cannot write to %s" % hosts_file
        sys.exit(1)

    return (hosts_lines, hosts_blob)

def get_sshconfig(cfg_file):
    """ Reads the content of cfg_file as if it were an ssh config file.
        Args:
            cfg_file - filename
        Returns:
            file content as string.
    """
    if os.path.exists(cfg_file):
        if not os.access(cfg_file, os.R_OK):
            print "Error: we cannot read to %s" % cfg_file
            sys.exit(1)
        cfg = open(cfg_file, 'r')
        cfg_blob = cfg.read()
        cfg.close()
    else:
        # NOTE: file doesn't exist yet, no big deal.
        cfg_blob = ""

    if not has_write_access(cfg_file):
        print "Error: we cannot write to %s" % cfg_file
        sys.exit(1)

    return cfg_blob

def append_file(filename, entry):
    if DEBUG:
        print "DEBUG: write(%s,%s)" % (filename, entry)
    else:
        fd = open(filename, 'a')
        if VERBOSE: print entry
        print >>fd, entry
        fd.close()

def add_config_entry(hostname, username, hosts_file, cfg_file, cfg_blob):
    """ Adds an ssh config entry for an M-Lab host to cfg_file, if not already
        in cfg_blob
    """
    cfgentry = "Host %s\n  HostName %s\n  Port 806\n  User %s\n"
    cfgentry+= "  UserKnownHostsFile %s\n"
    cfgentry = cfgentry % (hostname[:11], hostname, username, hosts_file)
    found = re.search(cfgentry, cfg_blob, re.MULTILINE)
    if not found:
        print "Adding entry for %s to %s" % (hostname, cfg_file)
        append_file(cfg_file, cfgentry)

def add_knownhosts_entry(hostname, ipaddress, sshkey, hosts_file, hosts_lines,
                        hosts_blob, update):
    """ Adds a plain (unhashed), ssh known_hosts entry for an M-Lab host to
        hosts_file, if not already in hosts_lines.  If the new entry is not
        found when 'update' is true, then an pre-existing entry that matches
        the same hostname:ipaddress pair is updated to have the new key.
    """

    # NOTE: [] are escaped for literal match in regular expression.
    search_entry_short  = "\[%s\]:806,\[%s\]:806"
    search_entry_short %= (hostname,ipaddress)

    # NOTE: just a flat string, not a regex.
    full_entry  = "[%s]:806,[%s]:806 %s"
    full_entry %= (hostname,ipaddress,sshkey)

    if full_entry not in hosts_lines:
        found = re.search(search_entry_short, hosts_blob, re.MULTILINE)
        if update and found:
            # NOTE: updates will require a modern ssh-keygen with '-R'
            print "Found know_hosts entry %s" % hostname
            print "Needs to be updated, so removing it..."
            cmd = "ssh-keygen -R [%s]:806 -f %s" % (ipaddress, hosts_file)
            if VERBOSE: print cmd
            os.system(cmd)
            # NOTE: set found to false, to trigger full entry addition below
            found = False
        elif found:
            # NOTE: the full entry is missing but the short form is found
            #       but update is not set.  So, warn user.
            print "WARNING: --update not given, and"
            print "WARNING: entry for %s is not current." % hostname

        if not found:
            print "Adding entry for %s to %s" % (hostname, hosts_file)
            append_file(hosts_file, full_entry)

def main(options):
    hosts_file = os.environ['HOME'] + "/.ssh/known_hosts_mlab"
    cfg_file = os.environ['HOME'] + "/.ssh/config"

    api = getapi()
    host2v4v6key = get_mlabhosts(api, options)

    if (options.knownhosts or options.update):
        (hosts_lines, hosts_blob) = get_knownhosts(hosts_file)

    if options.config:
        cfg_blob = get_sshconfig(cfg_file)

    # for each mlab host add the config and knownhost entries if missing
    for (hostname,(ipv4,ipv6,key)) in host2v4v6key.items():

        if options.config:
            # args: hostname, username, ...
            add_config_entry(hostname, options.user, hosts_file,
                             cfg_file, cfg_blob)

        if ipv4 is not None and (options.knownhosts or options.update):
            add_knownhosts_entry(hostname, ipv4, key, hosts_file, hosts_lines,
                                 hosts_blob, options.update)

        # NOTE: not all nodes have ivp6 addrs.
        if ipv6 is not None and (options.knownhosts or options.update):
            add_knownhosts_entry(hostname, ipv6, key, hosts_file, hosts_lines,
                                 hosts_blob, options.update)

def parse_options():
    global VERBOSE
    global DEBUG

    from optparse import OptionParser
    parser = OptionParser(usage=usage())

    parser.set_defaults(knownhosts=False,
                        update=False,
                        config=False,
                        user="root",
                        verbose=False,
                        debug=False)

    parser.add_option("-v", "--verbose", dest="verbose", action="store_true",
                      help="Verbose mode: print extra details.")
    parser.add_option("-d", "--debug", dest="debug", action="store_true",
                      help="Debug mode: perform no updates.")

    parser.add_option("", "--knownhosts", dest="knownhosts", action="store_true",
                      help="Only append new knownhosts entries.")
    parser.add_option("", "--update", dest="update", action="store_true",
                      help="Append and 'update' known_hosts entries, if changed.")

    parser.add_option("", "--config", dest="config", action="store_true",
                      help="Also add individual host aliases in ~/.ssh/config")
    parser.add_option("", "--user", dest="user",
                      help="Username for ssh config. 'root' or slicename.")

    parser.add_option("", "--hostpattern", dest="hostpattern",
                      default="*measurement-lab.org",
                      help="The simple regex for matching hostnames in PLCAPI")

    # NOTE: make it clear what is returned.
    (options, args) = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    VERBOSE = options.verbose
    DEBUG = options.debug

    return (options, args)

def usage():
    return """
SUMMARY:
 --knownhosts:
    The script fetches host SSH keys from PLC and writes host entries
    for the IPv4 and IPv6 addresses to:
       ~/.ssh/known_hosts_mlab

    For entries already present, no change is made.  No deletes are performed
    for now-missing entries.

    If you pass "--update" on the command line, then out-of-date entries are
    updated with current values from PLC.

    The script will not work if HashKnownHosts is 'yes'.  Hashed values
    intentionally obfuscate the known_host entries: meaning to leak less
    information. But, this also prevents identifying already-present entries.

 --config:
    If you pass "--config" and "--user" on the command line, an alias is created
    automatically for every host referencing the known_hosts_mlab file above:
        Host <mlab1.sit01>
          HostName <mlab1.sit01>.measurement-lab.org
          Port 806
          User <user>
          UserKnownHostsFile ~/.ssh/known_hosts_mlab

    This makes short-form hostnames like the following:
        ssh mlab1.vie01

    Map to:
        ssh -p806 -oUserKnownHostsFile=~/.ssh/known_hosts_mlab \\
            <user>@mlab1.vie01.measurement-lab.org

    If you don't use "--config" then you should manually add an entry like the
    following to your ~/.ssh/config and some pre-existing aliases:
        UserKnownHostsFile ~/.ssh/known_hosts_mlab

 authentication:
    PlanetLab does not report whitelisted nodes via anonymous access. So, you
    must log in using your PlanetLab credentials.

    The first run of this script asks for your PL credentials and then creates a
    7 day session, stored in:
        ~/.ssh/ssh_mlab_session

    Using establishing a session, the script makes authenticated API calls to
    get a list of mlab hosts & ips.

EXAMPLE:
    ./get-mlab-sshconfig.py --help
    ./get-mlab-sshconfig.py --knownhosts
    ./get-mlab-sshconfig.py --update
    ./get-mlab-sshconfig.py --update --config --user <slicename>
"""

if __name__ == "__main__":
    (options, args) = parse_options()
    main(options)
