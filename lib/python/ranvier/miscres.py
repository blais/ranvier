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

# hume imports
from hume import authentication, umusers, umprivileges
from hume.resources.umres import login_redirect


#-------------------------------------------------------------------------------
#
class Redirect(Resource):
    """
    Simply redirect to a fixed location.
    """
    def __init__( self, target, **kdws ):
        Resource.__init__(self, **kwds)
        self._target = target

    def handle( self, ctxt ):
        ctxt.response.redirect(self._target)


#-------------------------------------------------------------------------------
#
class TestMapper(Resource):
    """
    Test the mapper.
    """
    def __init__( self, mapper, **kwds ):
        Resource.__init__(self, **kwds)
        self.mapper = mapper

    def handle( self, ctxt ):
        ctxt.response.setContentType('text/html')

        # FIXME todo


#-------------------------------------------------------------------------------
#
class LogRequests(DelegaterResource):

    fmt = '----------------------------- %s'

    def handle_this( self, ctxt ):
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

    def handle_this( self, ctxt ):
        for c in xrange(self.count):
            ctxt.locator.next()


#-------------------------------------------------------------------------------
#
class UserObj(Resource):
    """
    A resource handler that allows specifying a username in the path.
    This is more or less an example.
    """
    def __init__( self, users, resource, **kwds ):
        Resource.__init__(self, **kwds)
        self.resource = resource
        self.users = users

    def handle( self, ctxt ):
        if verbosity >= 1:
            ctxt.log("resolver: %s" % ctxt.locator.path[ctxt.locator.index:])
        if ctxt.locator.isleaf():
            # no username specified
            return ctxt.response.errorNotFound()

        username = ctxt.locator.current()
        try:
            ctxt.user = self.users[username]
        except KeyError:
            return ctxt.response.errorNotFound()

        ctxt.locator.next()
        return self.resource.handle(ctxt)


#-------------------------------------------------------------------------------
#
class LeafPage(Resource):
    def handle( self, ctxt ):
        if not ctxt.locator.isleaf():
            return ctxt.response.errorNotFound()


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


class UserRoot(resource.DelegaterResource):
    """
    A handler that interprets the path component as a username and sets that
    user in the args for consumption by later handlers.
    """
    digitsre = re.compile('^\d+$')

    def __init__( self, next_resource, no_error=False, **kwds ):
        resource.DelegaterResource.__init__(self, next_resource, **kwds)
        self._no_error = no_error

    def enum( self, enumv ):
        enumv.declare_var('user', self.getnext())

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


#-------------------------------------------------------------------------------
#
class LogRequestsWithUser(resource.DelegaterResource):

    fmt = '-----------[%05d] %s'
        
    def handle_this( self, ctxt ):
        ctxt.log(self.fmt % (authentication.userid() or 0, ctxt.locator.uri()))

