#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Path locator class.
"""

# stdlib imports
import sys
from os.path import join, normpath


#-------------------------------------------------------------------------------
#
class HandlerContext(object):
    """
    Handler context.  This is an object meant to contain a locator and for
    clients to put other stuff that should be passed around in the chain of
    handlers.
    """
    def __init__( self, uri, args, root=None ):

        self.locator = PathLocator.from_uri(uri, root=root)
        """Locator object that is updated between handler to handler."""

        self.args = args
        """Arguments, as they come from the framework."""

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
    def from_uri( uri, root=None ):
        trailing = False
        if uri.endswith('/'): # remove trailing / if present
            trailing = True
        path = [x for x in uri.split('/') if x]
        p = PathLocator(path, trailing, root)
        return p

    def __init__( self, path, trailing=False, root=None ):
        self.root = root
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
            root = self.root or '/'
            r = root + '/'.join(self.path[:idx])
        else:
            r = self.root or ''
        r += (self.trailing and '/' or '')
        return r

    def current_uri( self ):
        return self.uri(self.index)


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

