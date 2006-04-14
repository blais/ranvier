#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Response proxy: an base class for adapting to other web frameworks.

The response proxy provides an interface which you can derive from to integrate
the default resources provided by this framework into any framework.
"""

# stdlib imports
import sys, string, StringIO
from os.path import join, normpath
import types


#-------------------------------------------------------------------------------
#
class ResponseProxy(object):
    """
    Response proxy object.
    """
    def setContentType( self, contype ):
        """
        Sets the content type, perhaps even sends it to the client.
        """
        raise NotImplementedError

    def write( self, text ):
        """
        Write the given text to the output stream (to the client).
        """
        raise NotImplementedError

    def errorNotFound( self, msg=None ):
        """
        Signal an error to the client indicating that the resource was not
        found (404).
        """
        raise NotImplementedError

    def errorForbidden( self, msg=None ):
        """
        Signal an error to the client indicating that accessing the resource was
        forbidden.
        """
        raise NotImplementedError

    def redirect( self, target ):
        """
        Redirect the client's browser to another URL.
        """
        raise NotImplementedError


#-------------------------------------------------------------------------------
#
class CGIResponse(ResponseProxy):
    """
    Simplistic response class for CGI programs.
    """
    def __init__( self, outfile=None ):
        ResponseProxy.__init__(self)

        self.contype = 'text/plain'
        """Content type, to be output upon first write."""

        self.wrotect = False
        """Flag to indicate if we have written yet."""

        if outfile is None:
            outfile = sys.stdout
        self.outfile = outfile

    def setContentType( self, contype ):
        self.contype = contype

    def write( self, text ):
        # Output content type header if we haven't yet done that.
        if not self.wrotect:
            self.outfile.write('Content-type: %s\n\n' % self.contype)
            self.wrotect = True
        self.outfile.write(text)

    def errorNotFound( self, msg=None ):
        if msg is None:
            msg = 'Document Not Found'
        for line in ('Content-type:', 'text/plain'
                     'Status: 404 %s' % msg,
                     ''):
            self.outfile.write(line)
            self.outfile.write('\n')

    def errorForbidden( self, msg=None ):
        if msg is None:
            msg = 'Access Denied'
        for line in ('Content-type:', 'text/plain'
                     'Status: 404 %s' % msg,
                     ''):
            self.outfile.write(line)
            self.outfile.write('\n')

    def redirect( self, target ):
        for line in ('Content-type:', 'text/plain'
                     'Status: 403 Access denied.',
                     ''):
            self.outfile.write(line)
            self.outfile.write('\n')

