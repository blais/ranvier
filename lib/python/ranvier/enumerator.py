#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Enumerator classes for making declartions for mapper.
"""

# ranvier imports
from ranvier import RanvierError
from ranvier.resource import Resource


__all__ = ('Enumerator',)


#-------------------------------------------------------------------------------
#
class EnumVisitor(object):
    """
    Visitor for enumerators.  This class has methods so that the resources may
    declare what resources they delegate to, what path components they consume
    and which are variables.  This is meant to be the interface that the
    resource object uses to declare possible delegations to other handlers in
    the chain of responsibility.
    """

    def __init__(self):
        self.branchs = []
        """A list of the possible branchs for a specific resource node.  This
        list takes on the form of a triple of (type, resource, arg), where arg
        is either None, a fixed component of a variable name depending on the
        type of the branch."""

        self.leaf = None
        """Flag that indicates if the visited node can be served as a leaf."""

        self.leaf_var = None
        """Variable for the leaf, if any."""


    def _add_branch(self, kind, delegate, arg):
        if not isinstance(delegate, Resource):
            raise RanvierError("Delegate %s must be derived from Resource." %
                               delegate)
        self.branchs.append( (kind, delegate, arg) )

    # Each of the three following functions declares an individual branch of the
    # resource tree.

    def declare_target(self, varname=None, default=None, format=None):
        """
        Declare that the given resource may serve the contents at this point in
        the path (this does not have to be a leaf, this could be used for a
        directory: e.g. if the request is at the leaf, we serve the directory
        contents).

        'varname' can be used to declare that it consumes some path components
        as well (optional).
        """
        if self.leaf:
            raise RanvierError("Error: Resource is twice declared as a leaf.")
        self.leaf = True

        if varname is not None:
            self.leaf_var = (varname, default, format)

        elif not (default is None and format is None):
                raise RanvierError("Error: You cannot declare a default or "
                                   "format without a variable.")

    def branch_anon(self, delegate):
        """
        Declare an anonymous delegate branch.
        """
        self._add_branch(Enumerator.BR_ANONYMOUS, delegate, None)

    def branch_static(self, component, delegate):
        """
        Declare the consumption of a fixed component of the locator to a
        delegate branch.
        """
        self._add_branch(Enumerator.BR_FIXED, delegate, component)

    def branch_var(self, varname, delegate, default=None, format=None):
        """
        Declare a variable component delegate.  This is used if your resource
        consumes a variable path of the locator.
        """
        self._add_branch(Enumerator.BR_VARIABLE, delegate,
                         (varname, default, format))

    def get_branches(self):
        """
        Accessor for branches.
        """
        return self.branchs

    def isleaf(self):
        """
        Returns true if the visited node has declared itself a leaf.
        """
        return self.leaf


#-------------------------------------------------------------------------------
#
class Enumerator(object):
    """
    A class used to visit and enumerate all the possible URL paths that are
    served by a resource tree.
    """
    BR_ANONYMOUS, BR_FIXED, BR_VARIABLE = xrange(3)
    """Delegate types."""

    def __init__(self):
        self.accpaths = []
        """The entire list of accumulated paths resulting from the traversal."""

    def visit_root(self, resource):
        return self.visit(resource, [], 0)

    def visit(self, resource, path, level):
        """
        Visit a resource node.  This method calls itself recursively.
        * 'resources' is the resource node to visit.
        * 'path' is the current path of components and variables that this
          visitor is currently at.
        """
        # Visit the resource and let it declare the properties of its
        # propagation/search.
        visitor = EnumVisitor()
        resource.enum_targets(visitor)

        # Get the accumulated branches.
        branches = visitor.get_branches()

        # If we have reached a leaf node (i.e. the node has declared itself a
        # potential leaf), add the path to the list of paths.
        if visitor.isleaf():

            # If this resource is a leaf and it does not have any other possible
            # branches, it is a terminal resource.  This is used later to
            # determine if we need append a trailing slash or not.
            isterminal = bool(branches)

            if visitor.leaf_var:
                # Append a path with a variable component at the end.
                path = path + [(Enumerator.BR_VARIABLE, None, visitor.leaf_var)]
                self.accpaths.append( (path, isterminal) )
            else:
                self.accpaths.append( (list(path), isterminal) )

        # Process the possible paths.  This is a breadth-first search.
        for branch in branches:
            kind, delegate, arg = branch
            self.visit(delegate, path + [branch], level+1)

    def getpaths(self):
        return self.accpaths

