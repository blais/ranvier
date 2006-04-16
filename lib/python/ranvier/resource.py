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
    Base class for all resources.
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

