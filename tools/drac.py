#!/usr/bin/env python

import sys
import os
import subprocess
import time
import getpass

DEBUG=False
VERBOSE=False
cookies = "--insecure --cookie-jar .cookies.txt --cookie .cookies.txt"
PREFIX=os.path.dirname(os.path.realpath(__file__))

def system(cmd):
    ## NOTE: use this rather than os.system() to catch
    ##       KeyboardInterrupt correctly.
    if DEBUG:
        print cmd
        # simulate success without running the command.
        return 0
    if VERBOSE:
        print cmd
    return subprocess.call(cmd, stdout=sys.stdout, 
                           stderr=sys.stderr, shell=True)

REBOOT_MESSAGE="""
NOTE: please send this message to ops@measurementlab.net:

Around %(ts)s we rebooted this server due to the system not responding:

    %(hostname)s

Once the reboot completes, all services on this system should return to normal.
"""

def usage():
    return """
    usage:
        All commands take a host specification.  A host spec is a FQHN, or a
        shorter pattern.  For example, "mlab1.nuq01", or "mlab1d.nuq01"
        without quotes are valid host specs and may be used interchangably.

        drac.py <host spec>

            Take hostname argument and print out associated PCU information.
            <hostname> may be a pattern, such as '*.site.measurement-lab.org'.
            Acts like the original 'drac-password.py' script.

        drac.py reboot <drac host spec>

            Use DRAC to reboot <hostname>

        drac.py shell <drac host spec>

            Take the drac-hostname argument and log into the DRAC interface via
            SSH.  Then, control is returned to the user to enter DRAC commands
            in the shell. i.e. reboot, or get system info, etc.

        drac.py console5 <drac host spec>
        drac.py console6 <drac host spec>

            Take the drac-hostname argument and open the JavaWebStart Virtual 
            Console.  This depends upon correct configuration of JavaWebStart, 
            which is platform dependent.  Check that 'javaws' is in your path.

            console5 is for  DRAC5
                ams01, ams02, atl01, dfw01, ham01, iad01, lax01, lga01, lga02, 
                lhr01, mia01, nuq01, ord01, par01, sea01, 

            console6 is for iDRAC6
                arn01, ath01, ath02, dub01, hnd01, mad01, mil01, syd01, syd02, 
                tpe01, vie01, wlg01, 

            unknown
                svg01, 

            unsupported (hpilo)
                trn01

            Not all systems have been tested. There may not be 100% coverage
            for MLab DRAC's.

        drac.py getsysinfo <drac host spec>

            Take the hostname argument and log into the DRAC interface via
            SSH.  Then run 'racadm getsysinfo'.
            <hostname> may be a pattern, such as '*.site.measurement-lab.org'.

        drac.py resetpassword <drac host spec> <newpassword>

            Take the drac-hostname and set a new password.
            The current password is taken from the PCU entry in the PLC 
            database.  Then, this command will log into the DRAC interface 
            and reset the password there.  Finally, it will update PLC's PCU 
            entry.
    """

def parse_options():

    from optparse import OptionParser
    parser = OptionParser(usage=usage())

    parser.set_defaults(promptpassword=False,
                        user="admin",
                        verbose=False,
                        debug=False)

    parser.add_option("-v", "--verbose", dest="verbose", action="store_true",
                        help="Verbose mode: print extra details.")

    parser.add_option("-n", "--dryrun", dest="debug", action="store_true",
                        help="Debug mode: perform no updates.")

    parser.add_option("-u", "--user", dest="user",
                        metavar="admin",
                        help=("The DRAC username. Should be used with '-p'"))
    parser.add_option("-p", "--promptpassword", dest="promptpassword",
                        action="store_true",
                        help=("Prompt for DRAC password rather than querying "+
                              "PLC.  This is useful if you do not have a PLC "+
                              "account"))

    (options, args) = parser.parse_args()

    if len(args) == 0:
        parser.print_help()
        sys.exit(1)

    command   = "list"
    host_spec = None
    newpasswd = None

    if len(args) == 1:
        host_spec = args[0]

    elif len(args) == 2:
        command = args[0]
        host_spec = args[1]

    elif len(args) == 3:
        command = args[0]
        host_spec = args[1]
        newpasswd = args[2]

    return (command, host_spec, newpasswd, options, args)

def hspec_to_pcu(host_spec):
    f = host_spec.split(".")
    suffix = "measurement-lab.org"

    if len(f) == 2: ## short form.
        if f[0][-1] == 'd':  ## already a pcu name.
            return host_spec + "." + suffix
        else:
            return "%sd.%s." % (f[0],f[1]) + suffix

    elif len(f) == 4: ## long form
        if f[0][-1] == 'd':   ## already a pcu name.
            return host_spec
        else:
            f[0] = f[0]+"d"
            return ".".join(f)
    else:
        return host_spec
    return None

def drac_formatLoginRequest(username, passwd):
    def escapeStr(val):
        escstr=""
        val = val.replace("\\", "\\\\")
        tmp = [ i for i in val ]
        for i in range(0,len(val)):
            if tmp[i] in ['@','(',')',',',':','?','=','&','#','+','%']:
                dec = ord(tmp[i])
                escstr+= "@0"+ "%02x" % dec
            else:
                escstr+=tmp[i]
        return escstr
    postData = ('user=' + escapeStr(username) +
                '&password=' + escapeStr(passwd))
    return postData

def drac_getLoginURL(console):
    if console == "console5":
        login_url = "cgi-bin/webcgi/login"
    elif console == "console6":
        login_url = "data/login"
    else:
        print "unknown console type: %s" % console
        sys.exit(1)
    return login_url

def drac_login(login_url, postData, hostname, output):
    ret = run_curl(hostname, login_url,
                   output, "-d '%s'" % postData)
    return ret

def run_curl(hostname, url, output, extra_args=""):
    cmd_fmt = "curl -D /tmp/out.headers %s -s %s -o %s 'https://%s/%s'"
    ret = system(cmd_fmt % (extra_args, cookies, output, hostname, url))
    if ret != 0:
        return False

    if DEBUG:
        # if DEBUG is true, out.headers will not exist, and it doesn't matter
        return True

    headers = open("/tmp/out.headers", 'r').read().strip()
    if VERBOSE:
        print headers

    if "200 OK" in headers or "302 Found" in headers:
        return True

    return False

def drac_downloadConsoleJNLP(console, user, passwd, hostname, jnlp_output):
    date_s=int((time.time())*1000)
    postData = drac_formatLoginRequest(user, passwd)
    login_url = drac_getLoginURL(console)

    login_output = "/tmp/out.login"

    print "Logging in.."
    login_ok = drac_login(login_url, postData, hostname, login_output)
    if not login_ok:
        print "Failed to login to %s" % hostname
        return False

    if VERBOSE: system("cat "+login_output); time.sleep(10)
    print "Getting *.jnlp for Java Web Start."
    if console == "console5":
        return drac5_downloadConsoleJNLP(hostname, date_s, jnlp_output)
    elif console == "console6":
        return drac6_downloadConsoleJNLP(hostname, date_s,
                                         login_output, jnlp_output)
    else:
        raise Exception("Unrecognized console type: %s" % console)

def drac6_downloadConsoleJNLP(hostname, date_s, login_output, jnlp_output):
    cmd = (r"sed -e "+
           r"'s/.*forwardUrl>index.html\(.*\)<\/forwardUrl.*/\1/g'"+
           r" " + login_output + r" | tr '?' ' '")
    if DEBUG:
        print cmd
        token = "faketoken"
    else:
        token = os.popen(cmd, 'r').read().strip()

    ## NOTE: handle the many variations on a theme.
    if "ath01" in hostname or "syd01" in hostname:
        url = "viewer.jnlp(%s@0@%s)" % (hostname, date_s)
    elif len(token) > 10:
        url = "viewer.jnlp(%s@0@title@%s@%s)" % (hostname, date_s, token)
    else:
        url = "viewer.jnlp(%s@0@title@%s)" % (hostname, date_s)

    ret = run_curl(hostname, url, jnlp_output)
    if VERBOSE: system("cat "+ jnlp_output)
    return ret

def drac5_downloadConsoleJNLP(hostname, date_s, jnlp_output):

    print "Getting Virtual Console SessionID.."
    session_url="cgi-bin/webcgi/vkvm?state=1"
    session_ok = run_curl(hostname, session_url, "/tmp/tmp.out")
    if not session_ok: return session_ok

    cmd = ("cat /tmp/tmp.out | grep vKvmSessionId |"+
           " tr '<>' ' ' | awk '{print $5}' ")
    if DEBUG:
        print cmd
        kvmSessionId = "fakeSessionID"
    else:
        kvmSessionId = os.popen(cmd).read().strip()

    jnlp_url="vkvm/%s.jnlp" % kvmSessionId
    jnlp_ok = run_curl(hostname, jnlp_url, jnlp_output)

    # NOTE: <sessionid>.jnlp is not always valid, so try the second variation
    cmd = "grep 'was not found on this server' "+jnlp_output+" >/dev/null"
    not_found = system(cmd)
    if not_found == 0:
        print jnlp_ok, "Second attempt..."
        jnlp_url="cgi-bin/webcgi/vkvmjnlp?id=%s" % date_s
        jnlp_ok = run_curl(hostname, jnlp_url, jnlp_output)

    if VERBOSE: system("cat "+jnlp_output)
    return jnlp_ok

def get_pcu_fields(host_spec, options, return_ip=False):
    pcuname = hspec_to_pcu(host_spec)
    ret = []
    if options.promptpassword:
        passwd = getpass.getpass("DRAC passwd: ")
        ret = [(pcuname, options.user, passwd, "DRAC")]
    else:
        cmd=(PREFIX+"/plcquery.py --action=get --type pcu --filter hostname=%s "+
             "--fields hostname,username,password,model,ip") % pcuname
        if DEBUG: print cmd
        lines= os.popen(cmd, 'r').readlines()
        for line in lines:
            h_u_pw_model= line.strip().split()
            hostname = h_u_pw_model[0]
            user     = h_u_pw_model[1]
            passwd   = h_u_pw_model[2]
            model    = h_u_pw_model[3]
            ip       = h_u_pw_model[4]
            if return_ip:
                ret.append((hostname, user, passwd, model, ip))
            else:
                ret.append((hostname, user, passwd, model))
    return ret

def main():
    global DEBUG
    global VERBOSE
    (command, host_spec, newpasswd, options, args) = parse_options()

    DEBUG=options.debug
    VERBOSE=options.verbose

    ## NOTE: Make sure the session is setup correctly.
    ## Use os.system() b/c the custom system() function
    ## doesn't flush stdout correctly. :-/
    if not options.promptpassword:
        print "Verifying PLC Session...\n"
        cmd=PREFIX+"/plcquery.py --action=checksession"
        if DEBUG:
            print cmd
        else:
            os.system(cmd)

    if command == "shell":
        pcu_fields = get_pcu_fields(host_spec, options)
        print "Login can be slow. When you receive a prompt, try typing"
        print " 'help' or 'racadm help' for a list of available commands."
        print " 'exit' will exit the shell and 'drac.py' script.\n"
        for hostname,user,passwd,model in pcu_fields:
            system("expect %s/exp/SHELL.exp %s %s '%s'" %
                   (PREFIX, hostname, user, passwd))

    elif command in ["console6", "console5"]:
        pcu_fields = get_pcu_fields(host_spec, options)
        if len(pcu_fields) != 1:
            print "host spec '%s' did not return a solitary record" % host_spec
            sys.exit(1)

        (hostname,user,passwd,model) = pcu_fields[0]

        if model != "DRAC":
            msg = "Automatic console loading is not supported "
            msg+= "for this model PCU: %s." % model
            print msg
            sys.exit(1)

        print "Virtual Console depends on correct setup of JavaWebStart..."
        jnlp_output = "/tmp/out.jnlp"
        download_ok = drac_downloadConsoleJNLP(command, user, passwd,
                                                hostname, jnlp_output)
        if not download_ok:
            print "Failed to download JNLP file from %s" % hostname
            sys.exit(1)

        print "Loading JavaWebStart."
        system("javaws "+jnlp_output)

    elif command == "getsysinfo":
        pcu_fields = get_pcu_fields(host_spec, options)
        if len(pcu_fields) == 0:
            print "host spec '%s' did not return any records" % host_spec
            sys.exit(1)

        for hostname,user,passwd,model in pcu_fields:
            if model not in ["DRAC", "IMM", "HPiLO"]:
                print "%s is an unsupported PCU model" % model
                continue

            system("expect %s/exp/GETSYSINFO.exp %s %s '%s'" %
                   (PREFIX, hostname, user, passwd))

    elif command == "reboot":
        pcu_fields = get_pcu_fields(host_spec, options)
        if len(pcu_fields) == 0:
            print "host spec '%s' did not return any records" % host_spec
            sys.exit(1)

        for hostname,user,passwd,model in pcu_fields:
            if model in ["DRAC", "IMM", "HPiLO"]:
                system("expect %s/exp/REBOOT.exp %s %s '%s' %s %s" %
                       (PREFIX, hostname, user, passwd, model, options.debug))
            elif model == "OpenIPMI":
                cmd = "ipmitool -I lanplus -H %s -U %s -P '%s' power cycle"
                cmd = cmd % (hostname, user, passwd) 
                system(cmd)
            else:
                print "%s is an unsupported PCU model" % model
                continue
            ts = time.strftime("%b %d %H:%M UTC", time.gmtime())
            msg = REBOOT_MESSAGE % {'ts' : ts, 'hostname' : hostname }
            # TODO: add option to --send this message to ops@ list
            print msg

    elif command == "rebootdrac":
        # After a shell login, some pcus can be "reset". i.e.
        # TODO: IMM can be soft reset using 'resetsp'
        # TODO: DRAC can be soft reset using 'racreset soft'
        # TODO: HPiLO can be soft reset using 'reset /map1'
        pass

    elif command == "resetpassword":
        ## NOTE: be extra verbose for password resets, in case something goes
        ##       wrong, to see where.
        if options.promptpassword:
            print "Password resets are not supported without updating PLC db."
            print "Do not specify password prompt, and try again."
            sys.exit(1)

        pcu_fields = get_pcu_fields(host_spec, options)
        if len(pcu_fields) != 1:
            print "host spec '%s' did not return a single record" % host_spec
            sys.exit(1)

        (hostname,user,passwd,model) = pcu_fields[0]

        if model != "DRAC":
            print "Unsupported PCU model '%s' for password reset." % model
            sys.exit(1)

        cmd = ("expect %s/exp/RESET_PASSWORD.exp %s %s '%s' '%s'" %
               (PREFIX, hostname, user, passwd, newpasswd))
        # Always print, even if DEBUG is not on
        if not DEBUG: print cmd
        ret = system(cmd)

        if ret != 0:
            print "An error occurred resetting the password. Stopping"
            sys.exit(1)

        print "Updating password in PLC database."
        cmd = (PREFIX+"/plcquery.py --action=update --type pcu "+
               "--filter 'hostname=%s' "+
               "--fields 'password=%s'") % (hostname, newpasswd)
        # Always print, even if DEBUG is not on
        if not DEBUG: print cmd
        ret = system(cmd)
        if ret != 0:
            print "Password update may have failed."
            print ("Before proceeding double check that the password "+
                   "update was successful.")
            print "e.g. drac.py %s" % host_spec
            sys.exit(1)

    elif command == "list":
        if options.promptpassword:
            print "Password prompt is not supported for 'list'"
            sys.exit(1)

        pcu_fields = get_pcu_fields(host_spec, options, True)
        if len(pcu_fields) == 0:
            print "host spec '%s' did not return any records" % host_spec
            sys.exit(1)

        for hostname,user,passwd,model,ip in pcu_fields:
            print "host:         %s" % hostname[0:5]+hostname[6:]
            print "pcu hostname: https://%s" % hostname
            print "pcu IP:       %s" % ip
            print "pcu username: %s" % user
            print "pcu password: %s" % passwd
            print "pcu model:    %s" % model

if __name__ == "__main__":
    main()
