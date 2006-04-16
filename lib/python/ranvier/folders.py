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
        # Set whether we will redirect the root of the folder (as default) for
        # the client to display a trailing slash.
        self.redirect_leaf_as_dir = children.pop('_training_slash', True)

        self.update(children)

    def __str__( self ):
        return '<FolderBase object id %d>' % id(self)

    __repr__ = __str__

    def enum( self, enumv ):
        for name, resource in self.iteritems():
            enumv.declare_fixed(name, resource)

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

            return self.handle(ctxt)
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

        ctxt.locator.next()
        return self.delegate(child, ctxt)

    def handle( self, ctxt ):
        """
        Called to handle when this resource is requested as the leaf.
        """
        raise NotImplementedError

    def notfound( self, ctxt, name ):
        """
        Called when the child is not found, to return some child handler.
        """
        return None


#-------------------------------------------------------------------------------
#
class Folder(FolderBase):
    """
    A resource handler that simply eats a component of a path.
    This is used to implement the hierarchy walk of URL components.

    The default value can be either a string or a resource object.
    """

    def __init__( self, _default=None, **children ):
        """
        '_default' can be a string or a resource object.
        """
        FolderBase.__init__(self, **children)
        self._default = _default

        # Try to get the child as a resource the right way, if we can.
        if isinstance(_default, str):
            try:
                self._default = children[_default]
            except KeyError:
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

    def handle( self, ctxt ):
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
    def genmenu( self, ctxt ):
        oss = StringIO.StringIO()
        print >> oss, '<h1>Resources menu</h1>'
        print >> oss, '<ul>'
        for c in sorted(self.iterkeys()):
            path = join(ctxt.locator.uri(), c)
            print >> oss, '  <li><a href="%s">%s</a></li>' % (path, c)
        print >> oss, '</ul>'
        return oss.getvalue()

    def handle( self, ctxt ):
        """
        Render a very simple list of the contents of this page.
        """
        # If we have set a default, use it.
        if self._default is not None:
            return Folder.handle(self, ctxt)
        
        self.default_menu(ctxt)
        
    def default_menu( self, ctxt ):
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

