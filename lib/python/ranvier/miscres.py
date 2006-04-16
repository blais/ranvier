#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Miscallenious useful generic resource classes.
"""

# ranvier imports
import ranvier.mapper
from ranvier.resource import Resource
from ranvier import verbosity, RanvierError


#-------------------------------------------------------------------------------
#
class LeafResource(Resource):
    """
    Base class for all leaf resources.
    """
    def handle_base( self, ctxt ):
        # Just check that this resource is a leaf before calling the handler.
        if not ctxt.locator.isleaf():
            return ctxt.response.errorNotFound()

        return self.handle(ctxt)


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

    def handle_base( self, ctxt ):
        # Call the handler.
        rcode = self.handle(ctxt)

        # Support errors that does not use exception handling.  Typically it
        # would be better to raise an exception to unwind the chain of
        # responsibility, but I'm not one to decide what you like to do.  This
        # is all about flexibility.
        if rcode is not None:
            return True

        # Automatically forward to the delegate resource if there are not
        # errors.
        return self.delegate(self._next, ctxt)


#-------------------------------------------------------------------------------
#
class CompVarResource(DelegaterResource):
    """
    Resource base class that inconditionally consumes one path component and
    that forwards to another resource.  This resource does not allow being a
    leaf (this would be possible, you could implement that if desired).

    If you need to perform some validation, override the handle() method and
    signal an error if your check fails.  The component has been set on the
    context object.
    """
    def __init__( self, compname, next_resource, **kwds ):
        """
        'compname': if specified, we store the component under an attribute with
                    this name in the context.
        """
        DelegaterResource.__init__(self, next_resource, **kwds)
        assert isinstance(compname, str)
        self.compname = compname

    def enum( self, enumv ):
        enumv.declare_compvar(self.compname, self.getnext())

    def handle_base( self, ctxt ):
        if verbosity >= 1:
            ctxt.log("resolver: %s" % ctxt.locator.path[ctxt.locator.index:])

        # Make sure we're not at the leaf.
        if ctxt.locator.isleaf():
            # We're at the leaf; No component specified.
            return ctxt.response.errorNotFound()
        
        # Get the name of the current component.
        comp = ctxt.locator.current()
        
        # Store the component value in the context.
        if hasattr(ctxt, self.compname):
            raise RanvierError("Error: Context already has attribute '%s'." %
                               self.compname)
        setattr(ctxt, self.compname, comp)

        # Consume the component.
        ctxt.locator.next()

        # Handle the resource.
        return DelegaterResource.handle_base(self, ctxt)

    def handle( self, txt ):
        pass # Noop.

#-------------------------------------------------------------------------------
#
class Redirect(LeafResource):
    """
    Simply redirect to a fixed location, identified by a resource-id.  This uses
    the mapper in the context to map the target to an URL.
    """
    def __init__( self, targetid, **kwds ):
        Resource.__init__(self, **kwds)
        self.targetid = targetid

    def handle( self, ctxt ):
        target = ctxt.mapper.url(self.targetid)
        ctxt.response.redirect(target)


#-------------------------------------------------------------------------------
#
class LogRequests(DelegaterResource):
    """
    Log a header to the error file and delegate.
    """

    fmt = '----------------------------- %s'

    def handle( self, ctxt ):
        ctxt.log(self.fmt % ctxt.locator.uri())


#-------------------------------------------------------------------------------
#
class RemoveBase(DelegaterResource):
    """
    Resource that removes a fixed number of base components.
    """
    def __init__( self, count, next, **kwds ):
        DelegaterResource.__init__(self, next, **kwds)
        self.count = count

    def handle( self, ctxt ):
        while xrange(self.count):
            ctxt.locator.next()


#-------------------------------------------------------------------------------
#
class PrettyEnumResource(LeafResource):
    """
    Output a rather nice page that describes all the pages that are being served
    from the given mapper.
    """
    def __init__( self, mapper, **kwds ):
        Resource.__init__(self, **kwds)
        self.mapper = mapper

    def handle( self, ctxt ):
        ctxt.response.setContentType('text/html')
        ctxt.response.write(ranvier.mapper.pretty_render_mapper(self.mapper))

