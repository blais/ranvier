#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#
# $Source: /home/blais/repos/cvsroot/hume/app/lib/hume/locator.py,v $
# $Id: locator.py,v 1.2 2005/07/04 12:56:31 blais Exp $
#

"""
Path locator class.
"""

# stdlib imports
import sys
from os.path import join, normpath

# zope imports.
## from zope import interface
## implements = interface.implements
def implements( foo ): pass

# indra imports.
from indra.iresource import IHandlerContext, IPathLocator


#-------------------------------------------------------------------------------
#
class HandlerContext(object):
    """
    Handler context.  This is an object meant to contain a locator and for
    clients to put other stuff that should be passed around in the chain of
    handlers.
    """
    implements(IHandlerContext)

    def __init__( self, uri, args ):
        
        self.locator = PathLocator.from_uri(uri)
        """Locator object that is updated between handler to handler."""

        self.args = args
        """Arguments, as they come from the framework."""

        
#-------------------------------------------------------------------------------
#
class PathLocator(object):
    """
    Locator object used to resolve the paths.
    """
    implements(IPathLocator)

    @staticmethod
    def from_uri( uri ):
        trailing = False
        if uri.endswith('/'): # remove trailing / if present
            trailing = True
        path = [x for x in uri.split('/') if x]
        p = PathLocator(path, trailing)
        return p

    def __init__( self, path, trailing=False ):
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
            r = '/' + '/'.join(self.path[:idx])
        else:
            r = ''
        r += (self.trailing and '/' or '')
        return r

    def current_uri( self ):
        return self.uri(self.index)


#===============================================================================
# TEST
#===============================================================================

import unittest

class LocationTests(unittest.TestCase):

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
    
