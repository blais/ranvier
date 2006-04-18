#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Ranvier demo application.

This demonstrates the URL mapping capabilities of Ranvier.

Note: This simple web application is built with a simple CGI script and an
apache redirect rule to provide clean URLs for the mapping demo.  We do it like
this because this reduces long-term maintenance issues: CGI is not about to go
away and it is easy to configure on my server.  Further, it really shows that
the Ranvier package is framework-agnostic and that you can integrate it within
any web application framework out there.
"""

# stdlib imports
import sys, os, urlparse
from os.path import dirname, join
import cgitb; cgitb.enable()
import pprint
import cPickle as pickle

# Add the Ranvier libraries to the load-path to minimize configuration (this is
# *only* a CGI script after all).
root = dirname(dirname(sys.argv[0]))
sys.path.append(join(root, 'lib', 'python'))

# ranvier imports
from ranvier import *
from ranvier import respproxy

# local imports
import demoapp


#-------------------------------------------------------------------------------
#
rootloc = '/ranvier/demo'
callgraph_filename = '/tmp/relations'

#-------------------------------------------------------------------------------
#
def main():
    """
    CGI handler for debugging/dumping the contents of the source upload.
    """
    uri = os.environ['SCRIPT_URI']
    scheme, netloc, path, parameters, query, fragid = urlparse.urlparse(uri)

    # Create the application.
    #
    # Note: this is a bit silly, we recreate the entire resource tree on every
    # request.  In a "real" web application, your process is a running for a
    # long time and this happens only once for every child.
    mapper, root = demoapp.create_application(rootloc)

    # Get the CGI args.
    args = respproxy.cgi_getargs()

    # Create a proxy response object for the default resources provided with
    # Ranvier to use.
    response_proxy = respproxy.CGIResponse(sys.stdout)

    # Register a callgraph reporter.
    relations_file = open(callgraph_filename, 'a')
    mapper.enable_callgraph(FileCallGraphReporter(relations_file))

    # Handle the resource.
    mapper.handle_request(path, args, response_proxy,
                          page=demoapp.PageLayout(mapper))

    relations_file.close()

#-------------------------------------------------------------------------------
#
def trace( o ):
    """
    A new builtin hack, for debugging.
    """
    sys.stderr.write(pprint.pformat(o) + '\n')

import __builtin__
__builtin__.__dict__['pp'] = trace


#-------------------------------------------------------------------------------
#
if __name__ == '__main__':
    main()

