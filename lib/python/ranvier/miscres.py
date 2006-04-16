#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Pseudo resources, which use a path component as an argument for some action.
"""

# stdlib imports
import sys, string, StringIO, types, re
from os.path import join, normpath

# ranvier imports
from ranvier.resource import Resource
from ranvier import verbosity


#-------------------------------------------------------------------------------
#
class LeafResource(Resource):
    """
    Base class for all leaf resources.
    """
    def handle( self, ctxt ):
        # Just check that this resource is a leaf.
        if not ctxt.locator.isleaf():
            return ctxt.response.errorNotFound()

        return self.handle_leaf(ctxt)

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


#-------------------------------------------------------------------------------
#
class CompVarResource(DelegaterResource):
    """
    Resource base class that inconditionally consumes one path component and
    that forwards to another resource.  This resource does not allow being a
    leaf (this would be possible, you could implement that if desired).
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

    def handle( self, ctxt ):
        if verbosity >= 1:
            ctxt.log("resolver: %s" % ctxt.locator.path[ctxt.locator.index:])

        if ctxt.locator.isleaf():
            # This is a leaf; No component specified.
            return ctxt.response.errorNotFound()
        
        comp = ctxt.locator.current()
        if self.handle_component(ctxt, comp):
            return True

        ctxt.locator.next()
        return self.forward(ctxt)

    def handle_component( self, ctxt, component ):
        """
        Return true if the component fails to validate.
        Override this method if you want to provide a validation routine.
        """
        # By default we always validate and store the component in the context.
        setattr(ctxt, self.compname, comp)


#-------------------------------------------------------------------------------
#
class Redirect(Resource):
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

    fmt = '----------------------------- %s'

    def handle_this( self, ctxt ):
        ctxt.log(self.fmt % ctxt.locator.uri())

class LogRequestsWithUser(DelegaterResource):

    fmt = '-----------[%05d] %s'
        
    def handle_this( self, ctxt ):
        ctxt.log(self.fmt % (authentication.userid() or 0, ctxt.locator.uri()))


#-------------------------------------------------------------------------------
#
class RemoveBase(DelegaterResource):
    """
    Resource that removes a fixed number of base components.
    """
    def __init__( self, count, next, **kwds ):
        DelegaterResource.__init__(self, next, **kwds)
        self.count = count

    def handle_this( self, ctxt ):
        for c in xrange(self.count):
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
        ctxt.response.write(pretty_render_mapper(self.mapper))




















## # hume imports
## from hume import authentication, umusers, umprivileges
## from hume.resources.umres import login_redirect

#-------------------------------------------------------------------------------
#
class RequireAuth(Resource):
    """
    A handler which requires authentication to follow the request.
    """
    def __init__( self, nextres, **kwds ):
        Resource.__init__(self, **kwds)
        self._nextres = nextres

    def enum( self, enumv ):
        enumv.declare_anon(self._nextres)

    def handle( self, ctxt ):
        if not authentication.userid():
            return self.fail(ctxt)
        return self._nextres.handle(ctxt)

    def fail( self, ctxt ):
        """
        Called on authentication failure.
        """
        return ctxt.response.errorForbidden()


class RequireAuthViaLogin(RequireAuth):
    """
    A handler which requires authentication to follow the request.
    """
    def __init__( self, redirect, nextres, **kwds ):
        RequireAuth.__init__(self, nextres, **kwds)
        self.redirect = redirect

    def fail( self, ctxt ):
        login_redirect(self.redirect, ctxt.locator.uri(), ctxt.args)


class PrivilegesBase(Resource):
    """
    Class that initializes a set of privileges and a delegate resource.
    """
    def __init__( self, required_privileges, nextres, **kwds ):
        Resource.__init__(self, **kwds)
        if isinstance(required_privileges, types.StringType):
            required_privileges = [required_privileges]
        self._required_privileges = required_privileges
        self._nextres = nextres
        assert isinstance(nextres, Resource)

    def enum( self, enumv ):
        enumv.declare_anon(self._nextres)


class RequirePrivilege(PrivilegesBase):
    """
    A handler which requires any one of a list of privileges (OR) to follow the
    request.
    """
    def handle( self, ctxt ):
        if self._required_privileges:
            uid = authentication.userid()

            # You must be logged in to have any kind of privilege.
            if not uid:
                return ctxt.response.errorForbidden()

            # Check each privilege in turn and break on the first one that
            # authorises (this is an OR logical).
            for p in self._required_privileges:
                if umprivileges.authorise(uid, p):
                    break
            else:
                return ctxt.response.errorForbidden()

        return self._nextres.handle(ctxt)


class UserRoot(DelegaterResource):
    """
    A handler that interprets the path component as a username and sets that
    user in the args for consumption by later handlers.
    """
    digitsre = re.compile('^\d+$')

    def __init__( self, next_resource, no_error=False, **kwds ):
        DelegaterResource.__init__(self, next_resource, **kwds)
        self._no_error = no_error

    def enum( self, enumv ):
        enumv.declare_compvar('user', self.getnext())

    def handle_this( self, ctxt ):
        if ctxt.locator.isleaf():
            # no username specified
            return ctxt.response.errorNotFound()

        # allow those who can to access resources from obsolete users
        allowobs = umprivileges.authorise(authentication.userid(), 'obsolete')
        
        # accept either a userid (faster) or the username
        name = ctxt.locator.current()
        u = None
        if self.digitsre.match(name):
            try:
                u = umusers.getById(name, allowobs)
            except RuntimeError:
                if not self._no_error:
                    return ctxt.response.errorNotFound()
        else:
            # get user by username
            try:
                u = umusers.getByUser(name)
            except RuntimeError:
                if not self._no_error:
                    return ctxt.response.errorNotFound()

        # Add current user in arguments.
        ctxt.user = u

        # Consume path component in locator.
        ctxt.locator.next()


class UserChildren(PrivilegesBase):
    """
    Resource that serves the request as a public resource if it's a leaf, but
    whose children require the currently authenticated user to be the same as
    the user in the path (or to have certain privileges).  This is meant be used
    as a child under UserRoot (but not necessarily directly).
    """
    def handle( self, ctxt ):
        # if we're not a leaf (we leave the root as public)
        if not ctxt.locator.isleaf():
            # check the special privileges
            uid = authentication.userid()
            for p in self._required_privileges:
                if umprivileges.authorise(uid, p):
                    break
            else:
                # if no special privileges, require same user
                if ctxt.user.id != uid:
                    return ctxt.response.errorForbidden()

        return self._nextres.handle(ctxt)


