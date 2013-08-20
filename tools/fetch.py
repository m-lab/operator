#!/usr/bin/env python

import csv
import sys
import os

import vxargs
#from monitor import parser as parsermodule
#from monitor import common
#from automate import *

import csv
from glob import glob
import os
import time

def usage():
    return """
    fetch.py -- run a short bash script across many machines.

    The list of nodes is taken to be all MLab nodes, unless 
    otherwise specified.

    Most common parameters:
    --cmd <cmdname>
            This looks for a script named 'scripts/<cmdname>.sh' 
            and writes logs to 'logs/<cmdname>'.

            You can also define a 'post' script to automatically 
            run on all the output logs from <cmdname>.  If this 
            file 'scripts/<cmdname>-post.sh' exists, it is 
            executed with the log directory as its only argument.

    --rerun <extension=content>
            Rerun a command using the log files as the source of 
            the node list.  This is helpful for rerunning 
            commands on just a few nodes based on previous runs.

            status=255   matches all nodes with an error
            status=0     matches all nodes with a success

    Examples:

        ./fetch.py --cmd procs
        ./fetch.py --cmd procs --rerun status=255 --list
        ./fetch.py --cmd procs --rerun status=255
"""

def time_to_str(t):
	return time.strftime("%Y/%m/%d %H:%M:%S", time.gmtime(t))

def csv_to_hash(r):
	ret = {}
	for line in r:
		(k,v) = (line[0], line[1])
		if k not in ret:
			ret[k] = v
		else:
			# multiple values for the same key
			if isinstance(ret[k], list):
				ret[k].append(v)
			else:
				ret[k] = [ret[k], v]
	return ret

def getcsv(file):
	return csv_to_hash(csv.reader(open(file,'r')))

def get_hostlist_from_dir(dirname, which):
    f = which.split("=")
    if len(f) > 1:
        suffix = f[0]
        value = f[1]
    else:
        suffix = f[0]
        value = None

    ret = glob(dirname + "/*.%s" % suffix)
    if value:
        ret_list = []
        for fname in ret:
            v = open(fname, 'r').read().strip()
            if value in v:
                ret_list.append(fname)
        ret = ret_list

    ret_list = []
    for fname in ret:
		ret_list.append([os.path.basename(fname)[:-(len(suffix)+1)], ''])

    return ret_list

def build_vx_args_external(shell_cmd):
    args = shell_cmd.split()
    return args

def vx_start_external(nodelist,outdir,cmd, timeout=0, threadcount=20):
    args = build_vx_args_external(cmd)
    vxargs.start(None, threadcount, nodelist, outdir, False, args, timeout)

def build_vx_args(shell_cmd):
    ssh_options="-q -o UserKnownHostsFile=junkssh -o StrictHostKeyChecking=no"
    cmd="""ssh -p806 %s root@[] """  % ssh_options
    args = cmd.split()
    args.append(shell_cmd)
    return args

def vx_start(nodelist,outdir,cmd, timeout=0, threadcount=20):
    args = build_vx_args(cmd)
    vxargs.start(None, threadcount, nodelist, outdir, False, args, timeout)

if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser(usage=usage())

    parser.set_defaults(outdir=None,
                        timeout=120,
                        simple=False,
                        threadcount=20,
                        external=False,
                        myopsfilter=None,
                        nodelist=None,
                        run=False,
                        list=False,
                        rerun=None,
                        template=None,
                        cmdline=None,
                        cmdfile=None,)

    parser.add_option("", "--cmd", dest="cmdfile", metavar="<cmdname>",
                        help=("This looks for a script named "+
                              "'scripts/<cmdname>.sh' and writes logs to "+
                              "'logs/<cmdname>'."))
    parser.add_option("", "--cmdline", dest="cmdline", metavar="<cmdline>",
                        help=("Uses string as explicit command to run on "+
                              "nodes. Writes logs to --outdir <outdir>."))
    parser.add_option("", "--rerun", dest="rerun", metavar="ext[=val]",
                        help=("Rerun fetch with the files indicated by the "+
                              "extension given to --rerun. For example, "+
                              "--rerun status=255, would rerun fetch on all "+
                              "files in --outdir that end with .status and "+
                              "have a value of 255"))
    parser.add_option("", "--outdir", dest="outdir", metavar="dirname",
                        help="Name of directory to place output.  If unset, "+
                             "automatically set to 'logs/<cmd>/'")
    parser.add_option("", "--nodelist", dest="nodelist", metavar="FILE", 
                        help=("Provide the input file for the list of objects,"+
                              " or explicit list 'host1,host2,host3' etc."))
    parser.add_option("", "--list", dest="list",  action="store_true",
                        help=("List the nodes the command would use; do "+
                              "nothing else."))
    parser.add_option("", "--timeout", dest="timeout", metavar="120",
                        help="Stop trying to execute after <timeout> seconds.")
    parser.add_option("", "--threadcount", dest="threadcount", metavar="20",
                        help="Number of simultaneous threads.")
    parser.add_option("", "--external", dest="external",  action="store_true",
                        help=("Run commands external to the server. The "+
                              "default is internal."))
    parser.add_option("", "--template", dest="template", 
                        help=("Command template for external commands; "+
                              "substitutes [] with hostname."))

    (config, args) = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    auto_outdir=None
    auto_script=None
    auto_script_post=None
    if config.cmdfile:
        if os.path.exists(config.cmdfile):
            f = open(config.cmdfile,'r')
        else:
            auto_script = "scripts/" + config.cmdfile + ".sh"
            auto_script_post = "scripts/" + config.cmdfile + "-post.sh"
            f = open(auto_script, 'r')
        cmd_str = f.read()
        auto_outdir="logs/" + config.cmdfile.split(".")[0]
    elif config.template and config.external:
        cmd_str = config.template
    elif config.cmdline:
        cmd_str = config.cmdline
    else:
        parser.print_help()
        sys.exit(1)

    if config.outdir == None and auto_outdir is None: 
        outdir="default_outdir"
    elif config.outdir == None and auto_outdir is not None:
        outdir=auto_outdir
    else: 
        outdir=config.outdir

    if not os.path.exists(outdir):
        os.system('mkdir -p %s' % outdir)
        assert os.path.exists(outdir)

    if config.nodelist is None and config.rerun is None:
        os.system("./plcquery.py --action=checksession")
        filename="/tmp/nodelist.txt"
        cmd="./plcquery.py --action=get --type node --filter hostname=*.measurement-lab.org " + \
            "--fields hostname > %s" % filename
        os.system(cmd)
        nodelist = vxargs.getListFromFile(open(filename,'r'))

    elif config.nodelist is not None:
        if os.path.exists(config.nodelist) and os.path.isfile(config.nodelist):
            nodelist = vxargs.getListFromFile(open(config.nodelist,'r'))
        elif not os.path.exists(str(config.nodelist)): 
            # NOTE: explicit list on command line "host1,host2,host3"
            nodelist = [ (host,'') for host in config.nodelist.split(",") ]

    elif config.rerun is not None and os.path.isdir(outdir):
        if config.rerun:
            nodelist = get_hostlist_from_dir(outdir, config.rerun)
        else:
            nodelist = get_hostlist_from_dir(outdir, "out")
    else:
        # probably no such file.
        raise Exception("Please specifiy a nodelist or --rerun directory" % config.nodelist)

    if config.list: 
        for n in sorted(nodelist, cmp, lambda x: x[0][::-1]):
            print n[0]
        sys.exit(0)

    if config.external or config.template is not None:
        vx_start_external(nodelist, outdir, cmd_str, int(config.timeout), int(config.threadcount))
    else:
        vx_start(nodelist, outdir, cmd_str, int(config.timeout), int(config.threadcount))

    if auto_script_post is not None and os.path.isfile(auto_script_post):
        os.system("bash %s %s" % (auto_script_post, outdir)) 
        
