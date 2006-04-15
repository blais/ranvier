#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Resource file.
"""

# stdlib imports
import sys, string, StringIO
from os.path import join, normpath
import types

# ranvier imports
from ranvier import verbosity


#-------------------------------------------------------------------------------
#
class Resource(object):
    """
    Concrete implementation of IResource.
    """
    __resid = None
    """Default resource-id used for URL mapping.  You usually do not need to set
    this, you can rely on the automatic class name transformation."""

    def __init__( self, **kwds ):
        resid = kwds.pop('resid', None)
        if resid is not None:
            self.__resid = resid

    def getresid( self, mapper ):
        """
        Given a resource instance, compute the resource-id to which it
        corresponds.

        Cool idea: this could be used by the template code to render the
        resource-id, e.g. in the HTML header.  This way the tests can be written
        to check for particular responses being completely oblivious of the
        actual URLs being used.
        """
        resid = self.__resid
        if resid is None:
            # Compute the resource-id from the name of the class.
            resid = mapper.namexform(self.__class__.__name__)
        assert resid
        return resid

    def enum( self, enumv ):
        """
        Enumerate all the possible resources that this resource may delegate to.
        This is used to produce the entire set of resources served by a resource
        tree.  See the enumerator class for more details.

        By default, if this resource is for leaf nodes, you don't need to do
        anything.  If this resource only deals with a component of the URL path,
        you need to declare all the possible resources that this delegates to.
        """
        # By default, no-op.

    def handle( self, ctxt ):
        """
        This is the handler.  This is where you get to do your doo-doo handling
        arguments and spitting HTML and shtuff.  You NEED to override this.
        """
        raise NotImplementedError


#-------------------------------------------------------------------------------
#
class DelegaterResource(Resource):
    """
    Resource base class for resources which do something and then
    inconditionally forward to another resource.  It used a template method to
    implement this simple behaviour.
    """
    def __init__( self, next_resource, **kwds ):
        Resource.__init__(self, **kwds)
        self._next = next_resource

    def getnext( self ):
        return self._next

    def enum( self, enumv ):
        enumv.declare_anon(self._next)

    def handle( self, ctxt ):
        # Handle this resource.
        rcode = self.handle_this(ctxt)

        # Support errors that does not use exception handling.  Typically it
        # would be better to raise an exception to unwind the chain of
        # responsibility, but I'm not one to decide what you like to do.  This
        # is all about flexibility.
        if rcode is not None:
            return True

        # Forwart to the delegate resource.
        self.forward(ctxt)

    def forward( self, ctxt ):
        self._next.handle(ctxt)

    def handle_this( self, ctxt ):
        raise NotImplementedError

