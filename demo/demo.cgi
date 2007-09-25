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



rootloc = '/ranvier/demo'

# Reporters
enable_callgraphs = 0
callgraph_filename = '/tmp/ranvier.callgraph'

# Reporters
enable_coverage = 1
coverage_filename = '/tmp/ranvier.coverage.dbm'



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
    mapper = UrlMapper(rootloc=rootloc)

    # Add tracing of resource path.
    tracer = TracerReporter(sys.stderr.write)
    mapper.add_reporter(tracer)

    # Create a coverage reporter, if requested.
    if enable_coverage:
        cov_reporter = DbmCoverageReporter('/tmp/ranvier.coverage.dbm')
        mapper.add_reporter(cov_reporter)
    else:
        cov_reporter = None

    # Register a resources callgraph reporter.
    if enable_callgraphs:
        callgraph_f = open(callgraph_filename, 'a')
        callgraph_reporter = FileCallGraphReporter(callgraph_f)
        mapper.add_reporter(callgraph_reporter)

    demoapp.create_application(mapper, cov_reporter)

    # Get the CGI args.
    args = respproxy.cgi_getargs()

    # Create a proxy response object for the default resources provided with
    # Ranvier to use.
    response_proxy = respproxy.CGIResponse(sys.stdout)

    # Handle the resource.
    method = os.environ['REQUEST_METHOD']
    mapper.handle_request(method, path, args, response_proxy,
                          page=demoapp.PageLayout(mapper))

    if enable_callgraphs:
        mapper.remove_reporter(callgraph_reporter)
        callgraph_f.close()

    if enable_coverage:
        mapper.remove_reporter(cov_reporter)
        del cov_reporter

    mapper.remove_reporter(tracer)



if __name__ == '__main__':
    main()

