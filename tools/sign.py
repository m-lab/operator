#!/usr/bin/env python

import sys
import os
import subprocess

DEBUG=False
def usage():
    return """
    sign.sh captures the basic commands for creating pub/priv keys,
    signing and verifying signatures with a public key.
        
    commands:
        create
            creates a public/private key pair.

        sign <filename> 
            generates a signature for file using private key

        verify <filename> 
            verifies signature for a file using public key

        sshsign <filename> 
            generates a signature for file using your private SSH key
            accepts:
                -i,--identity <identity file>

        sshverify <filename> 
            verifies signature for a file using public SSH key
            accepts:
                -i,--identity <identity file>
    """

def parse_args():
    from optparse import OptionParser
    parser = OptionParser(usage=usage())
    parser.add_option("-v", "--verbose", dest="verbose", 
                       default=False, 
                       action="store_true", 
                       help="Verbose mode: print extra details.")
    parser.add_option("-i", "--identity", dest="identity", 
                       default=os.environ['HOME']+"/.ssh/id_rsa", 
                       metavar="~/.ssh/id_rsa",
                       help="The SSH identity to use for signing & verifying")
    parser.add_option("-d", "--debug", dest="debug",  action="store_true",
                       default=False,
                       help="Print shell commands as they are executed.")

    (options, args) = parser.parse_args()

    if len(sys.argv) == 1: 
        parser.print_help()
        sys.exit(1)
        
    return (options, args)

def system(cmd):
    ## NOTE: use this rather than os.system() to catch KeyboardInterrupts correctly.
    if DEBUG: print cmd
    return subprocess.call(cmd, stdout=sys.stdout, 
                           stderr=sys.stderr, shell=True,
                           executable='/bin/bash')

def main():
    global DEBUG
    (options, args) = parse_args()
    DEBUG = options.debug
    if len(args) > 0:
        command = args[0]
        filename=None
        if len(args) > 1:
            filename = args[1]
    
    if DEBUG:
        print command, filename, options.identity

    if command == "create":
        system("openssl genrsa -out private.pem 1024")
        system("openssl rsa    -in  private.pem -pubout > public.pem")

    elif command == "sign":
        system("openssl dgst -sha256 -sign private.pem \
                                    -out '%s.sig' '%s'" % (filename, filename))

    elif command == "verify":
        system("openssl dgst -sha256 -verify public.pem \
                              -signature '%s.sig' '%s'" % (filename, filename))

    elif command == "sshsign":
        system("openssl dgst -sha256 -sign %s '%s' > '%s.sig'" %
                    (options.identity, filename, filename) )

    elif command == "sshverify":
        system("openssl dgst -sha256 \
            -verify <( ssh-keygen -e -f %s -m PKCS8 ) \
            -signature '%s.sig' '%s'" % (options.identity, filename, filename))

    else:
        usage()
        sys.exit(1)

if __name__ == "__main__":
    main()
