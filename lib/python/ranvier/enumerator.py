# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Enumerator classes for making declartions for mapper.
"""

# ranvier imports
from ranvier import RanvierError


__all__ = ('Enumerator',)



class EnumVisitor(object):
    """
    Visitor for enumerators.  This class has methods so that the resources may
    declare what resources they delegate to, what path components they consume
    and which are variables.  This is meant to be the interface that the
    resource object uses to declare possible delegations to other handlers in
    the chain of responsibility.
    """

    def __init__(self, resource):
        self.resource = resource
        """The resource being visited."""
        
        self.branchs = []
        """A list of the possible branchs for a specific resource node.  This
        list takes on the form of pairs of (resource, component to be added)"""

        self.leaf = None
        """Flag that indicates if the visited node can be served as a leaf.
        This takes the same form as the list of branches."""

        self.optparams = []
        """Optional parameters."""

    # Each of the three following functions declares an individual branch of the
    # resource tree.

    def declare_target(self, varname=None, format=None):
        """
        Declare that the given resource may serve the contents at this point in
        the path (this does not have to be a leaf, this could be used for a
        directory: e.g. if the request is at the leaf, we serve the directory
        contents).

        'varname' can be used to declare that it consumes some path components
        as well (optional).
        """
        if self.isleaf():
            raise RanvierError("Error: Resource is declared twice as a leaf.")

        if format and not varname:
            raise RanvierError("Error: You cannot declare a format without "
                               "a variable.")
        
        if varname is None:
            self.leaf = (self.resource, None)
        else:
            self.leaf = (self.resource, VarComponent(varname, format))

    def declare_optparam(self, varname, format=None):
        """
        Declare an optional query parameter that this node consumes. Query
        parameters are the arguments specified after the `?' as in ::

           /users/<user>)/index?category=<category>

        They are used to allow back-mapping URLs with a single syntax.  In the
        example, above, this would be::

           mapurl('@@IndexForUser', <user>, category=<category>)

        """
        if not isinstance(varname, str):
            raise RanvierError(
                "Error: optional parameter names must be strings.")
        
        self.optparams.append( OptParam(varname, format) )

    def branch_anon(self, delegate):
        """
        Declare an anonymous delegate branch.
        """
        self.branchs.append( (delegate, None) )

    def branch_static(self, component, delegate):
        """
        Declare the consumption of a fixed component of the locator to a
        delegate branch.
        """
        assert isinstance(component, str), "Component name must be string."
        self.branchs.append( (delegate, FixedComponent(component)) )

    def branch_var(self, varname, delegate, format=None):
        """
        Declare a variable component delegate.  This is used if your resource
        consumes a variable path of the locator.
        """
        assert isinstance(varname, str), "Variable name must be string."
        assert isinstance(format, (type(None), str)), "Format must be string."
        self.branchs.append( (delegate, VarComponent(varname, format)) )

    def get_branches(self):
        """
        Accessor for branches.
        """
        return self.branchs

    def get_optparams(self):
        """
        Accessor for branches.
        """
        return self.optparams

    def isleaf(self):
        """
        Returns true if the visited node has declared itself a leaf.
        """
        return self.leaf is not None



class Enumerator(object):
    """
    A class used to visit and enumerate all the possible URL paths that are
    served by a resource tree.
    """
    def __init__(self):
        self.accpaths = []
        """The entire list of accumulated paths resulting from the traversal."""

    def visit_root(self, resource):
        return self.visit(resource, [], [], 0)

    def visit(self, resource, components, optparams, level):
        """
        Visit a resource node.  This method calls itself recursively.
        * 'resources' is the resource node to visit.
        * 'components' is the current list of components and variables that this
          visitor is currently at.
        """
        # Visit the resource and let it declare the properties of its
        # propagation/search.
        visitor = EnumVisitor(resource)
        resource.enum_targets(visitor)

        # Get the accumulated branches.
        branches = visitor.get_branches()

        # Update the optparams for this node and its branches.
        new_optparams = optparams + visitor.get_optparams() # Makes a copy.

        # If we have reached a leaf node (i.e. the node has declared itself a
        # potential leaf), add the components to the list of componentss.
        if visitor.isleaf():

            # If this resource is a leaf and it does not have any other possible
            # branches, it is a terminal resource.  This is used later to
            # determine if we need append a trailing slash or not.
            isterminal = bool(branches)
            
            # Update the list of components for the list.
            leafres, leafcomp = visitor.leaf
            leaf_components = list(components)
            if leafcomp is not None:
                leaf_components.append(leafcomp)

            # Add the leaf as a valid path.
            self.accpaths.append(
                (leafres, leaf_components, new_optparams, isterminal) )

        # Process the possible paths.  This is a breadth-first search.
        for branch_res, branch_comp in branches:
            # Update the list of components for the child.
            child_components = list(components)
            if branch_comp:
                child_components.append(branch_comp)

            # Visit the children, recursively.
            self.visit(branch_res, child_components, new_optparams, level+1)

    def getpaths(self):
        """
        Return a list of (path, isterminal, optparams) paths.
        """
        return self.accpaths




class Component(object):
    """
    Base class for URI path components.
    """

class FixedComponent(Component):
    """
    A fixed component.
    """
    def __init__(self, name):
        self.name = name

    def __cmp__(self, other):
        return cmp(self.name, other.name)

class VarComponent(Component):
    """
    A variable component.
    """
    def __init__(self, varname, format=None):
        self.varname = varname

        # Remove leading %, if present.
        if format and format.startswith('%'):
            format = format[1:]

        self.format = format

    def __cmp__(self, other):
        c = cmp(self.varname, other.varname)
        if c != 0:
            return c
        return cmp(self.format, other.format)

class OptParam(object):
    """
    Optional parameter.
    """
    def __init__(self, varname, format=None):
        self.varname = varname

        if format and format.startswith('%'):
            format = format[1:]
        self.format = format


