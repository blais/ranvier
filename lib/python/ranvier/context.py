#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Path locator class.
"""

# stdlib imports
import sys, types
from os.path import join


__all__ = ('HandlerContext', 'InternalRedirect')


#-------------------------------------------------------------------------------
#
class HandlerContext(object):
    """
    Handler context.  This is an object meant to contain a locator and for
    clients to put other stuff that should be passed around in the chain of
    handlers.
    """
    def __init__( self, uri, args, rootloc=None ):

        self.locator = PathLocator.from_uri(uri, rootloc)
        """Locator object that is updated between handler to handler."""

        self.args = args
        """Arguments, as they come from the framework."""

    def redirect( self, uri, args=None ):
        """
        Internal redirect using a Ranvier exception.
        """
        raise InternalRedirect(uri, args)

        # Note: We might consider in the future providing a method that accepts
        # a resource-id, but this will require also providing a way to enter the
        # resource mapping's parameters.  For now, it's not pretty enough, if
        # you want to do this, use the following syntax::
        #
        #   ctxt.redirect(ctxt.mapurl(resid, ...), args)

    def log( self, msg ):
        """
        Print a message to the server's error log.  The default implementation
        just prints on stderr.  Override this method in a derived class if you
        need real logging.
        """
        sys.stderr.write(msg)
        sys.stderr.write('\n')


#-------------------------------------------------------------------------------
#
class PathLocator(object):
    """
    Locator object used to resolve the paths.
    """
    @staticmethod
    def from_uri( uri, rootloc=None ):
        trailing = False
        if uri.endswith('/'): # remove trailing / if present
            trailing = True
        path = [x for x in uri.split('/') if x]
        p = PathLocator(path, trailing, rootloc)
        return p

    def __init__( self, path, trailing=False, rootloc=None ):
        self.rootloc = rootloc
        self.path = path
        self.index = 0
        self.trailing = trailing

    def __str__( self ):
        return '<PathLocator %s %s>' % (self.path, self.index)

    def current( self ):
        return self.path[self.index]

    def getnext( self ):
        return self.path[self.index+1]

    def next( self ):
        self.index += 1
        return self

    def isleaf( self ):
        return self.index == len(self.path)

    def uri( self, idx=1000 ):
        if self.path:
            rootloc = self.rootloc or '/'
            r = join(rootloc, '/'.join(self.path[:idx]))
        else:
            r = self.rootloc or ''
        r += (self.trailing and '/' or '')
        return r

    def current_uri( self ):
        return self.uri(self.index)


#-------------------------------------------------------------------------------
#
class InternalRedirect(Exception):
    """
    Exception that you can use to perform internal redirects.  It is caught and
    dealt and handled by the mapper so it's transparent to your application
    framework.
    """
    def __init__( self, uri, args=None ):
        Exception.__init__(self, "Internal redirection to '%s'." % uri)
        assert isinstance(uri, str)
        assert isinstance(args, (types.NoneType, dict))
        self.uri, self.args = uri, args



#===============================================================================
# TEST
#===============================================================================

import unittest

class Tests(unittest.TestCase):

    def test_simple( self ):
        loc = PathLocator.from_uri('')
        self.assert_(loc.path == [])
        self.assert_(loc.trailing is False)
        self.assert_(loc.uri() == '')

        loc = PathLocator.from_uri('/')
        self.assert_(loc.path == [])
        self.assert_(loc.trailing is True)
        self.assert_(loc.uri() == '/')

        loc = PathLocator.from_uri('/bli')
        self.assert_(loc.path == ['bli'])
        self.assert_(loc.trailing is False)
        self.assert_(loc.uri() == '/bli')

        loc = PathLocator.from_uri('/bli/')
        self.assert_(loc.path == ['bli'])
        self.assert_(loc.trailing is True)
        self.assert_(loc.uri() == '/bli/')

        loc = PathLocator.from_uri('/bli/gugu')
        self.assert_(loc.path == ['bli', 'gugu'])
        self.assert_(loc.trailing is False)
        self.assert_(loc.uri() == '/bli/gugu')

        loc = PathLocator.from_uri('/bli/gugu/')
        self.assert_(loc.path == ['bli', 'gugu'])
        self.assert_(loc.trailing is True)
        self.assert_(loc.uri() == '/bli/gugu/')

if __name__ == '__main__':
    unittest.main()

