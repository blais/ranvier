#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Folder-style resources, for implementing static paths.
"""

# stdlib imports
import StringIO
from os.path import join, normpath
import types

# ranvier imports
from ranvier import verbosity, RanvierError
from ranvier.resource import Resource


#-------------------------------------------------------------------------------
#
class FolderBase(Resource, dict):
    """
    Base class for resources which contain other resources.
    """
    def __init__( self, **children ):
        Resource.__init__(self, **children)
        children.pop('resid', None)

        # Set whether we will redirect the root of the folder (as default) for
        # the client to display a trailing slash.
        self.redirect_leaf_as_dir = children.pop('_training_slash', True)

        self.update(children)

    def __str__( self ):
        return '<FolderBase object id %d>' % id(self)

    __repr__ = __str__

    def enum( self, enumv ):
        for name, resource in self.iteritems():
            enumv.branch_static(name, resource)

    def handle_base( self, ctxt ):
        if verbosity >= 1:
            ctxt.log("resolver: %s" %
                        ctxt.locator.path[ctxt.locator.index:])

        if ctxt.locator.isleaf():
            if verbosity >= 1:
                ctxt.log("resolver: at leaf")

            if not ctxt.locator.trailing and self.redirect_leaf_as_dir:
                # If a folder resource is requested by default, redirect so that
                # relative paths will work in that directory.
                return ctxt.response.redirect(ctxt.locator.uri() + '/')

            return self.handle_default(ctxt)
        # else ...
        name = ctxt.locator.current()

        if verbosity >= 1:
            ctxt.log("resolver: getting named child %s" % name)
        try:
            child = self[ name ]
            if not isinstance(child, Resource):
                msg = "resolver: child is not a resource: %s" % child
                ctxt.log(msg)
                raise RanvierError(msg)

        except KeyError:
            # Try fallback method.
            child = self.notfound(ctxt, name)

            if child is None:
                if verbosity >= 1:
                    ctxt.log("resolver: child %s not found" % name)
                return ctxt.response.errorNotFound()

        if verbosity >= 1:
            ctxt.log("resolver: child %s found, calling it" % name)

        # Let the folder do some custom handling.
        if self.handle(ctxt):
            return True

        ctxt.locator.next()
        return self.delegate(child, ctxt)

    def notfound( self, ctxt, name ):
        """
        Called when the child is not found, to return some child handler.
        """
        return None

    def handle( self, ctxt ):
        """
        Called everytime control passes through this resource.
        """
        # Noop.

    def handle_default( self, ctxt ):
        """
        Called to handle when this resource is requested as the leaf.
        """
        raise NotImplementedError


#-------------------------------------------------------------------------------
#
class Folder(FolderBase):
    """
    A resource handler that simply eats a component of a path.
    This is used to implement the hierarchy walk of URL components.

    The default value can be either a string or a resource object.
    """

    def __init__( self, **children ):
        """
        If '_default' is specified, it should be a string or a resource object
        to the default resource.
        """
        self._default = children.pop('_default', None)
        FolderBase.__init__(self, **children)

        # Try to get the child as a resource the right way, if we can.
        if isinstance(self._default, str):
            try:
                self._default = children[self._default]
            except KeyError:
                # We keep the default as a string for the next time we reference
                # it, we'll try again.
                pass
            
    def __setitem__( self, key, value ):
        dict.__setitem__(self, key, value)

        if isinstance(self._default, str) and self._default == key:
            self._default = value

    def getdefault( self ):
        if isinstance(self._default, str):
            # The default is a string, the name of the child, this must be
            # the first time it is called, we replace it by the actual
            # resource object for the next calls.
            try:
                self._default = self[self._default]
            except KeyError:
                raise RanvierError(
                    "Error: folder default child '%s' not found" %
                    self._default)

        assert isinstance(self._default, (types.NoneType, Resource))
        return self._default

    def handle_default( self, ctxt ):
        default = self.getdefault()
        if default is None:
            if verbosity >= 1:
                ctxt.log("resolver: no default page set")
            # no default page submitted, indicate error
            return ctxt.response.errorNotFound()
        else:
            # Default is a Resource, delegate to it.
            self.delegate(default, ctxt)


#-------------------------------------------------------------------------------
#
class FolderWithMenu(Folder):
    """
    A folder resource handler who can render a default page that lists and
    allows access to all the subresources it contains.
    """
    def enum( self, enumv ):
        Folder.enum(self, enumv)

        # This menu may be served as a leaf.
        enumv.declare_serve()

    def genmenu( self, ctxt ):
        oss = StringIO.StringIO()
        print >> oss, '<h1>Resources menu</h1>'
        print >> oss, '<ul>'
        for c in sorted(self.iterkeys()):
            path = join(ctxt.locator.uri(), c)
            print >> oss, '  <li><a href="%s">%s</a></li>' % (path, c)
        print >> oss, '</ul>'
        return oss.getvalue()

    def handle_default( self, ctxt ):
        """
        Render a very simple list of the contents of this page.
        """
        menu = self.genmenu(ctxt)
        template = '''
<html>
  <head>
    <title>Folder menu</title>
  </head>
  <body>
    %s
  </body>
</html>
'''
        ctxt.response.setContentType('text/html')
        ctxt.response.write(template % menu)

