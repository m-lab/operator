#!/usr/bin/env python


import sys
import getpass
import xmlrpclib
import os
import sys
import re

SESSION_DIR=os.environ['HOME'] + "/.ssh"
SESSION_FILE=SESSION_DIR + "/query_mlab_session"
API_URL = "https://boot.planet-lab.org/PLCAPI/"
VERBOSE=False
DEBUG=False

class API:
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
    print "PLC Email: ",
    sys.stdout.flush()
    username = sys.stdin.readline().strip()
    password = getpass.getpass("PLC Password: ")
    auth = {'Username' : username,
            'AuthMethod' : 'password',
            'AuthString' : password}
    plc = API(auth, API_URL)
    session = plc.GetSession(60*60*24*30)
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
                print "Refresh your PLC session file: %s" % SESSION_FILE
                sys.stdout.flush()
                refreshsession()
        except:
            #import traceback
            #traceback.print_exc()
            print "Setup a new PLC session file: %s" % SESSION_FILE
            sys.stdout.flush()
            refreshsession()

    assert auth is not None
    return API(auth, API_URL)

def parse_comma_sep_fields(fields):
    if fields:
        s = fields.split(",")
        if s == []:
            return None
        else:
            return s
    else:
        return None

def parse_query_filter(filter):
    if filter is None:
        return None
    ret = {}
    for filt in parse_comma_sep_fields(filter):
        s = filt.split("=")
        if len(s) == 2:
            v = s[1]
            try:
                v = int(v)
            except:
                v = str(v)
            ret.update({s[0] : v})
        else:
            raise Exception("filter format should be name=value")
    return ret

def conv(s):
    # strip non-ascii characters to prvent errors
    r = "".join([x for x in s if ord(x) < 128])
    return r

def print_fields(obj, fields, format):
    if format:
        for f in obj:
            if type(obj[f]) in (str, unicode): 
                obj[f] = conv(obj[f])
            
        print format % obj
    else:
        for f in fields:
            if f in obj:
                if type(obj[f]) in (str,unicode):
                    obj[f] = conv(obj[f])
                elif type(obj[f]) in [type([])]:
                    obj[f] = " ".join([ str(x) for x in obj[f] ])
                print obj[f],
        print ""

def list_fields(l):
    if len(l) > 0:
        o = l[0]
        for k in o.keys():
            print k
        sys.exit(1)
    else:
        print "no objects returned to list fields"
        sys.exit(1)

def parse_options():

    from optparse import OptionParser
    parser = OptionParser()

    parser.set_defaults(
                        action="get",
                        type='node',
                        filter=None,
                        fields=None,
                        format=None,
                        listfields=False,
                        withsitename=False,
                        byloginbase=None,
                        byrole=None,
                        verbose=False, 
                        debug=False, 
                        )

    parser.add_option("-v", "--verbose", dest="verbose", action="store_true", 
                        help="Verbose mode: print extra details.")

    parser.add_option("-d", "--debug", dest="debug", action="store_true", 
                        help="Debug mode: perform no updates.")

    parser.add_option("", "--action", dest="action", 
                        metavar="[get|update|delete|add]", 
                        help="Set the action type for query")

    parser.add_option("", "--type", dest="type", 
                        metavar="[node|pcu|person|site]", 
                        help="object type to query")

    parser.add_option("", "--filter", dest="filter", 
                        metavar="name=value", 
                        help=("Filter passed to action=get calls; For "+
                              "action=update calls, filter should "+
                              "be specific enough to match only 1 object."))

    parser.add_option("", "--fields", dest="fields", 
                    metavar="key,list,...", 
                    help=("For action=get:\n"+
                          "\t- a list of keys to display for each object.\n"+
                          "For action=update:\n"+
                          "\t- a list of key=value pairs to update."))

    parser.add_option("", "--format", dest="format",
                        help="Format string to use to print")
    parser.add_option("", "--byloginbase", dest="byloginbase",
                        help="")
    parser.add_option("", "--byrole", dest="byrole",
                        help="")
    parser.add_option("", "--withsitename", dest="withsitename",
                        action="store_true", help="")

    parser.add_option("", "--listfields", dest="listfields", 
                        action="store_true",
                        help="A list of nodes to bring out of debug mode.")

    if len(sys.argv) == 0: 
        parser.print_help()
        sys.exit(1)

    (options, args) = parser.parse_args()

    # Default filters for some object types
    if options.action == "get" and \
       options.type   == "node"  and \
       options.filter is None:
        options.filter = "hostname=*.measurement-lab.org"
        options.fields = "hostname"
    elif options.action == "get" and \
       options.type   == "pcu"  and \
       options.filter is None:
        options.filter = "hostname=*.measurement-lab.org"
        options.fields = "hostname,username,password"

    global VERBOSE
    global DEBUG
    VERBOSE = options.verbose
    DEBUG = options.debug

    return (options, args)

def get_pcu_id(api, obj_id):
    try:
        retid = int(obj_id)
        return retid
    except:
        ret = api.GetPCUs(obj_id, ['pcu_id'])
        if len(ret) == 1:
            retid = ret[0]['pcu_id']
            return retid
        raise Exception("GetPCUs returned %s results for %s; expected 1" % (
                        len(ret), obj_id))

def get_node_id(api, obj_id):
    try:
        retid = int(obj_id)
        return retid
    except:
        ret = api.GetNodes(obj_id, ['node_id'])
        if len(ret) == 1:
            retid = ret[0]['node_id']
            return retid
        raise Exception("GetNodes returned %s results for %s; expected 1" % (
                        len(ret), obj_id))

def handle_update(api, config, obj_filter, fields):
    if config.type == 'node': 
        if config.fields is None: 
            config.fields='hostname'
            fields = parse_comma_sep_fields(config.fields)

        node_id = get_node_id(api, obj_filter)
        n = api.UpdateNode(node_id, fields)
        print n

    if config.type == 'pcu': 
        if config.fields is None: 
            print "WARNING: you must provide fields to update"
            sys.exit(1)

        fields = parse_query_filter(config.fields)
        pcu_id = get_pcu_id(api, obj_filter)
        u = api.UpdatePCU(pcu_id, fields)
        print u

    if config.type == 'site': 
        print "Site update is unimplemented" 
        sys.exit(1)

    if config.type == 'person': 
        print "Person update is unimplemented" 
        sys.exit(1)
    
def handle_get(api, config, filtr, fields):
    if config.type == 'node': 
        if config.fields is None: 
            config.fields='hostname'
            fields = parse_comma_sep_fields(config.fields)

        n = api.GetNodes(filtr, fields)
        if config.listfields: list_fields(n)
        for i in n:
            print_fields(i, fields, config.format)

    if config.type == 'pcu': 
        if config.fields is None: 
            config.fields='hostname,username,password'
            fields = parse_comma_sep_fields(config.fields)

        n = api.GetPCUs(filtr, fields)
        if config.listfields: list_fields(n)
        for i in n:
            print_fields(i, fields, config.format)
        
    if config.type == 'site': 
        print "Site query is unimplemented" 
        sys.exit(1)

    if config.type == 'person': 
        print "WARNING: less tested" 
            
        if config.byloginbase:
            s = api.GetSites({'login_base' : config.byloginbase}, 
                             ['person_ids'])
            f = s[0]['person_ids']
        if config.byrole:
            p = api.GetPersons(None, ['person_id', 'roles'])
            p = filter(lambda x: config.byrole in x['roles'], p)
            f = [ x['person_id'] for x in  p ]

        if config.withsitename:
            n = api.GetPersons(f, fields)
            if config.listfields: list_fields(n)
            for i in n:
                sitelist = api.GetSites(i['site_ids'], ['person_ids', 'name'])
                if len(sitelist) > 0:
                    s = sitelist[0]
                    if i['person_id'] in s['person_ids']:
                        i['name'] = conv(s['name'])
                        print_fields(i, fields, config.format)
        else:
            n = api.GetPersons(f, fields)
            if config.listfields: list_fields(n)
            for i in n:
                print_fields(i, fields, config.format)

def main():
    (config, args) = parse_options()
    api = getapi()

    if config.action == "checksession":
        sys.exit(0)

    if config.action == "get":
        f = parse_query_filter(config.filter)
        fields = parse_comma_sep_fields(config.fields)
        handle_get(api, config, f, fields)

    if config.action == "update":
        filter_id = parse_query_filter(config.filter)
        if config.fields is None:
            print "WARNING: please provide fields to update"
            sys.exit(1)
        update_fields = parse_query_filter(config.fields)
        handle_update(api, config, filter_id, update_fields)

if __name__ == "__main__":
    main()
