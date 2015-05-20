#!/usr/bin/env python

import ConfigParser
import getpass
import os
import sys
import xmlrpclib
import ssl

API_URL = "https://boot.planet-lab.org/PLCAPI/"
PLC_CONFIG="/etc/planetlab.conf"
SESSION_DIR=os.environ['HOME'] + "/.ssh"
SESSION_FILE=SESSION_DIR + "/mlab_session"
SSL_CONTEXT = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
SSL_CONTEXT.load_verify_locations(os.path.dirname(os.path.realpath(__file__)) + "/../../boot.planet-lab.org.ca")

api = None

def setup_global_session(url, debug, verbose, plcconfig=None):
    global api
    global API_URL
    API_URL=url
    api = getapi(debug, verbose, plcconfig)
    return api

def read_plc_config(filename):
    """ Use python's ConfigParser() to extract user credentials from filename.
    File should include:
        [MyPLC]
        username=
        password=
    Args:
        filename - full path to config file
    Returns:
        (username, password) tuple
    Raises:
        ConfigParser.NoSectionError - when MyPLC section does not exist.
        ConfigParser.NoOptionError  - when value is not specified in section.
    """
    config = ConfigParser.SafeConfigParser()
    config.read(filename)
    un = config.get("MyPLC", "username")
    pw = config.get("MyPLC", "password")
    return (un, pw)

class API:
    def __init__(self, auth, url, debug=False, verbose=False):
        self.debug = debug
        self.verbose = verbose
        self.auth = auth
        self.api = xmlrpclib.Server(url, verbose=False, allow_none=True, context=SSL_CONTEXT)
    def __repr__(self):
        return self.api.__repr__()
    def __getattr__(self, name):
        run = True
        if self.debug and 'Get' not in name:
            # Do no run when debug=True & not a Get* api call
            run = False

        method = getattr(self.api, name)
        if method is None:
            raise AssertionError("method does not exist")

        #if self.verbose: 
        #    print "%s(%s)" % (name, params)

        def call_method(auth, *params):
            if self.verbose: 
                print "%s(%s)" % (name, params)
            return method(self.auth, *params)

        if run:
            return lambda *params : call_method(self.auth, *params)
        else:
            print "DEBUG: Skipping %s()" % name
            return lambda *params : 1

        #return lambda *params : call_method(*params)
        #return call_method(*params)

def refreshsession(plcconfig=None):
    # Either read session from disk or create it and save it for later
    if plcconfig is not None and os.path.exists(plcconfig):
        print "Using credentials from: ", plcconfig
        (username, password) = read_plc_config(plcconfig)
    else:
        print "PLC Username: ",
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
    session_map = parse_sessions(SESSION_FILE, fail_on_open=False)
    session_map[API_URL] = session
    write_sessions(SESSION_FILE, session_map)

def write_sessions(session_file, session_map):
    f = open(SESSION_FILE, 'w')
    for url in session_map.keys():
        print >>f, url, session_map[url]
    f.close()

def parse_sessions(session_file, fail_on_open=True):
    try:
        session_lines = open(SESSION_FILE, 'r').readlines()
    except:
        if fail_on_open: 
            # throw the error for someone else to catch
            raise
        else: 
            # return an empty map
            return {}

    session_map = {}
    for line in session_lines:
        f = line.strip().split()
        if len(f) == 0:
            continue
        elif len(f) == 1:
            print "old format session file: remove %s and rerun" % SESSION_FILE
            sys.exit(1)
        elif len(f) > 2:
            print "too many fields in session line"
            sys.exit(1)
        else:
            (url, session) = f
            session_map[url] = session
    return session_map

def getapi(debug=False, verbose=False, plcconfig=None):
    global api
    api = xmlrpclib.ServerProxy(API_URL, allow_none=True, context=SSL_CONTEXT)
    auth = None
    authorized = False
    while not authorized:
        try:
            auth = {}
            auth['AuthMethod'] = 'session'
            session_map = parse_sessions(SESSION_FILE)
            auth['session'] = session_map[API_URL]
            authorized = api.AuthCheck(auth)
            if not authorized:
                print "Need to refresh your PLC session file: %s" % SESSION_FILE
                sys.stdout.flush()
                refreshsession(plcconfig)
        except:
            print "Need to setup a new PLC session file: %s" % SESSION_FILE
            sys.stdout.flush()
            refreshsession(plcconfig)

    assert auth is not None
    return API(auth, API_URL, debug, verbose)

