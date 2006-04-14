#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#
# $Source: /home/blais/repos/cvsroot/hume/app/lib/hume/resource.py,v $
# $Id: resource.py,v 1.25 2005/07/01 03:16:14 blais Exp $
#

"""
A web resource mechanism, similar to that in Twisted.
"""

# stdlib imports
import sys, string, StringIO
from os.path import join, normpath
import types

# special imports
## from zope import interface
## implements = interface.implements
def implements( foo ): pass

# hume imports
from hume import logger, response, request


#-------------------------------------------------------------------------------
#
verbosity = 0


#-------------------------------------------------------------------------------
#
from indra.iresource import IResource

class Resource(object):
    """
    Concrete implementation of IResource.
    """
    implements(IResource)

    resid = None
    """Default resource-id used for URL mapping.  You usually do not need to set
    this, you can rely on the automatic class name transformation."""

    def __init__( self, **kwds ):
        resid = kwds.pop('resid', None)
        if resid is not None:
            self.resid = resid

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
class EnumVisitor(object):
    """
    Visitor for enumerators.  This class has methods so that the resources may
    declare what resources they delegate to, what path components they consume
    and which are variables.  This is meant to be the interface that the
    resource object uses to declare possible delegations to other handlers in
    the chain of responsibility.
    """

    def __init__( self ):
        self.delegates = []
        """A list of the possible delegates for a specific resource node.  This
        list takes on the form of a triple of (type, resource, arg), where arg
        is either None, a fixed component of a variable name depending on the
        type of the delegate."""

    def _add_delegate( self, kind, delegate, arg ):
        if not isinstance(delegate, Resource):
            raise RuntimeError("Class %s must be derived from Resource." %
                               delegate.__class__.__name__)
        self.delegates.append( (kind, delegate, arg) )

    def declare_anon( self, delegate ):
        """
        Declare an anonymous delegate.
        """
        self._add_delegate(Enumerator.ANON, delegate, None)

    def declare_fixed( self, component, delegate ):
        """
        Declare the consumption of a fixed component of the locator to a
        delegate.
        """
        self._add_delegate(Enumerator.FIXED, delegate, component)

    def declare_var( self, variable, delegate, default=None ):
        """
        Declare a variable component delegate.  This is used if your resource
        consumes a variable path of the locator.
        """
        self._add_delegate(Enumerator.VAR, delegate, (variable, default))

    def get_delegates( self ):
        """
        Accessor for delegates.
        """
        return self.delegates


class Enumerator(object):
    """
    A class used to visit and enumerate all the possible URL paths that are
    served by a resource tree.
    """
    ANON, FIXED, VAR = xrange(3)
    """Delegate types."""

    def __init__( self ):
        self.accpaths = []
        """The entire list of accumulated paths resulting from the traversal."""

    def visit_root( self, resource ):
        return self.visit(resource, [])

    def visit( self, resource, path ):
        """
        Visit a resource node.  This method calls itself recursively.

        * 'resources' is the resource node to visit.

        * 'path' is the current path of components and variables that this
          visitor is currently at.
        """
        # Visit the resource and let it declare the properties of its
        # propagation.
        # search.
        visitor = EnumVisitor()
        resource.enum(visitor)
        delegates = visitor.get_delegates()

        # If we have reached a leaf node, add the path to the list of paths.
        if not delegates:
            self.accpaths.append(list(path))
        else:
            # Process the possible paths.  This is a breadth-first
            for decl in delegates:
                kind, delegate, arg = decl
                self.visit(delegate, path + [decl])

    def getpaths( self ):
        return self.accpaths


#-------------------------------------------------------------------------------
#
class ReadOnlyDict(object):
    """
    A read-only dictionary.
    """
    def __init__( self, *params, **kwds ):
        self.rwdict = dict(*params, **kwds)

    def __getitem__( self, resid ):
        return self.rwdict(resid)

    def has_key( self, resid ):
        return self.rwdict.has_key(resid)

    def items( self ):
        return self.rwdict.items()

    def iteritems( self ):
        return self.rwdict.iteritems()

    def keys( self ):
        return self.rwdict.keys()

    def iterkeys( self ):
        return self.rwdict.iterkeys()

    def values( self ):
        return self.rwdict.values()

    def itervalues( self ):
        return self.rwdict.itervalues()


#-------------------------------------------------------------------------------
#
class UrlMapper(ReadOnlyDict):
    """
    A class that contains mappings from the resource names to the URLs to be
    constructed.  You need to initialize it with a root node that is traversed
    in order to build the mapping.

    These mappings are used when rendering pages rather than fixed URLs, to
    allow moving stuff around.  They also help create a conceptual barrier
    between the list of resources that your server provides and their address
    and parameters.  It is also a very safe way to force the creation of URLs
    that are always valid.
    """
    def __init__( self, resource_root=None, namexform=None ):
        ReadOnlyDict.__init__(self)

        self.mappings = self.rwdict
        """Mappings from resource-id to (url, defaults-dict, resource)
        triples."""

        self.namexform = namexform or slashslash_namexformer
        """A callable that is used to calculate an appropriate resource-id from
        the resource instance.  You can override this to provide your own
        favourite scheme."""

        if resource_root is not None:
            self.initialize(resource_root)

    def initialize( self, root ):
        """
        Add the resource from the given root to the current mapper.  You need to
        call this at least once before using the mapper to fill it with some
        values, and with resources at the same resource level.
        """
        enumv = Enumerator()
        enumv.visit_root(root)

        for path in enumv.getpaths():
            # Compute the URL string and a dictionary with the defaults.
            # Defaults that are unset are left to None.
            components = []
            defaults_dict = {}
            for kind, resource, arg in path:
                if kind is Enumerator.ANON:
                    continue
                elif kind is Enumerator.FIXED:
                    components.append(arg)
                elif kind is Enumerator.VAR:
                    varname, vardef = arg
                    defaults_dict[varname] = vardef
                    components.append('%%(%s)s' % varname)

            # Calculate the resource-id from the resource at the leaf.
            resid = self.getresid(path[-1][1])

            # Check that the resource-id has not already been seen.
            if resid in self.mappings:
                raise RuntimeError("Error: Duplicate resource id '%s'." % resid)

            # Add the mapping.
            self.mappings[resid] = ('/'.join(components),
                                    defaults_dict,
                                    resource)

    def getresid( self, resource ):
        """
        Given a resource instance, compute the resource-id to which it
        corresponds.

        Cool idea: this could be used by the template code to render the
        resource-id, e.g. in the HTML header.  This way the tests can be written
        to check for particular responses being completely oblivious of the
        actual URLs being used.
        """
        resid = resource.resid
        if resid is None:
            # Compute the resource-id from the name of the class.
            resid = self.namexform(resource.__class__.__name__)
        assert resid
        return resid

    def url( self, resid, **kwds ):
        """
        Map a resource-id to its URL, filling in the parameters and making sure
        that they are valid.  The keyword arguments are expected to match the
        required arguments for the URL exactly.  The resource id can be either

        * a string of the class
        * the class object of the resource (if there is only one
          of them instanced in the tree)
        * the instance of the resource
        """
        # Support passing in resource instances and resource classes as well.
        if isinstance(resid, Resource):
            resid = self.namexform(resid.__class__.__name__)
        elif isinstance(resid, type) and issubclass(resid, Resource):
            resid = self.namexform(resid.__class__.__name__)
        else:
            assert isinstanc(resid, (str, unicode))

        # Get the desired mapping.
        try:
            urlstr, defdict = self.mappings[resid]
        except KeyError:
            raise RuntimeError("Error: invalid resource-id '%s'." % resid)

        # Prepare the defaults dict with the provided values.
        params = defdict.copy()
        for cname, cvalue in kwds.iteritems():
            # Check all provided values are legal.
            if cname not in params:
                raise RuntimeError(
                    "Error: '%s' is not a valid component key for mapping the "
                    "'%s' resource.'" % (cname, resid))
            params[cname] = cvalue

        # Check that all the required values have been provided.
        missing = filter(cname for cname, cvalue in params.iteritems()
                         if cvalue is None)
        if missing:
            raise RuntimeError(
                "Error: Missing values attempting to map to a resource: %s" %
                ', '.join(missing))
                
        # Plop in the values.  This should always succeed here due to the checks
        # above.
        mapped_url = urlstr % params

        return '/' + mapped_url

    def inversemap( self ):
        """
        Return an inverse mapping of (url, resid, defdict) triples sorted by
        URL.
        """
        # Print each mapping, on a single line.
        invmap = [(url, resid, defdict, resource)
                      for resid, (url, defdict, resource) in self.iteritems()]
        invmap.sort()
        return invmap

    def render( self ):
        """
        Render the contents of the mapper so that it can be reconstructed from
        the given text, to be able to create some URLs.  This returns a list of
        lines (str) to output.

        Cool idea: This can be served from a resource (enabled only in test
        mode) on your server, so that the automated tests can use this to
        generate the URLs that they are testing.  This means that you could
        entirely shuffle the URLs in your web application and your entire test
        suite would still keep working.
        """
        invmap = self.inversemap()

        # Format for alignment for nice printing (and this does make the parsing
        # any more complicated.
        maxidlen = max(len(x[1]) for x in invmap)
        fmt = '%%-%ds : /%%s' % maxidlen

        return [fmt % (resid, url) for url, resid, defdict, res in invmap]

        # Note: we are considering whether rendering the defaults-dict would be
        # interesting for reconstructing the UrlMapper from a list of lines, as
        # would be done for generating test cases.  For now we ignore the
        # defdict.

    def pretty_render( self ):
        """
        Output an HTML representation of the contents of the mapper (a str).

        This representation is meant to serve to the user for debugging, and
        includes the docstrings of the resource classes, if present.
        """
        oss = StringIO.StringIO()
        oss.write('''
<html>
  <head>
    <title>URL Mapper Resources</title>
    <meta name="generator" content="Ranvier Pretty Resource Renderer" />
    <style type="text/css"><!--
body { font-family: Luxi Sans, Lucida, Arial, sans-serif; }
.resource-title { white-space: nowrap; }
p.docstring { margin-left: 2em; }
--></style>
 <body>
  <h1>URL Mapper Resources</h1>
''')

        invmap = self.inversemap()

        for url, resid, defdict, resource in invmap:
            # Prettify the URL somewhat for user readability.
            url = '/' + url.replace('%(', '[<i>').replace(')s', '</i>]')

            # Make the URL clickable it contains no parameters.
            if not defdict:
                url = '<a href="%s">%s</a>' % (url, url)

            m = {'resid': resid,
                 'url': url}
            oss.write('''
  <h2 class="resource-title">%(resid)s: <tt>%(url)s</tt></h2>
''' % m)
            if resource.__doc__:
                oss.write('  <p class="docstring">%s</p>' % resource.__doc__)

        oss.write('''
 </body>
</html>
''')
        return oss.getvalue()


#-------------------------------------------------------------------------------
#
def slashslash_namexformer( clsname ):
    """
    Use the class' name, separate capwords with dashes and prepend with two at
    signs, for easy grepping later on in the codebase/templates.
    """
    return '@@' + clsname


#-------------------------------------------------------------------------------
#
class EnumResource( Resource ):
    """
    Enumerate all the resources available from a resource tree.
    """
    def __init__( self, mapper, **kwds ):
        Resource.__init__(self, **kwds)
        self.mapper = mapper

    def handle( self, ctxt ):
        response.setContentType('text/plain')
        for line in self.mapper.render():
            response.write(line)
            response.write('\n')


class PrettyEnumResource(Resource):
    """
    Output a rather nice page that describes all the pages that are being served
    from the given mapper.
    """
    def __init__( self, mapper, **kwds ):
        Resource.__init__(self, **kwds)
        self.mapper = mapper

    def handle( self, ctxt ):
        response.setContentType('text/html')
        response.write(self.mapper.pretty_render())


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
        response.setContentType('text/html')




#-------------------------------------------------------------------------------
#
class WrapResource(Resource):
    """
    Resource base class for resources which do something and then forward to
    another resource.
    """
    def __init__( self, next_resource, **kwds ):
        Resource.__init__(self, **kwds)
        self._next = next_resource

    def getnext( self ):
        return self._next

    def enum( self, enumv ):
        enumv.declare_anon(self._next)

    def handle( self, ctxt ):
        self.handle_this(ctxt)
        self.forward(ctxt)

    def forward( self, ctxt ):
        self._next.handle(ctxt)

    def handle_this( self, ctxt ):
        raise NotImplementedError




#-------------------------------------------------------------------------------
#
class LogRequests(WrapResource):

    fmt = '----------------------------- %s'

    def handle_this( self, ctxt ):
        logger.info(self.fmt % ctxt.locator.uri())


#-------------------------------------------------------------------------------
#
class RemoveBase(WrapResource):
    """
    Resource that removes a fixed number of base components.
    """
    def __init__( self, count, next, **kwds ):
        WrapResource.__init__(self, next, **kwds)
        self.count = count

    def handle_this( self, ctxt ):
        for c in xrange(self.count):
            ctxt.locator.next()


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

    def handle( self, ctxt ):
        if verbosity >= 1:
            logger.info("resolver: %s" %
                        ctxt.locator.path[ctxt.locator.index:])

        if ctxt.locator.isleaf():
            if verbosity >= 1:
                logger.info("resolver: at leaf")

            if not ctxt.locator.trailing and self.redirect_leaf_as_dir:
                # If a folder resource is requested by default, redirect so that
                # relative paths will work in that directory.
                response.redirect(ctxt.locator.uri() + '/')

            return self.default(ctxt)
        # else ...
        name = ctxt.locator.current()

        if verbosity >= 1:
            logger.info("resolver: getting named child %s" % name)
        try:
            child = self[ name ]
            if not isinstance(child, Resource):
                msg = "resolver: child is not a resource: %s" % child
                logger.error(msg)
                assert RuntimeError(msg)

        except KeyError:
            # Try fallback method.
            child = self.notfound(ctxt, name)

            if child is None:
                if verbosity >= 1:
                    logger.info("resolver: child %s not found" % name)
                response.error(response.code.NotFound)

        if verbosity >= 1:
            logger.info("resolver: child %s found, calling it" % name)

        ctxt.locator.next()
        return child.handle(ctxt)

    def default( self, ctxt ):
        """
        Called to handle when this resource is requested as the leaf.
        """
        raise NotImplementedError

    def notfound( self, ctxt, name ):
        """
        Called when the child is not found, to return some child handler.
        """
        return None


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
        return self._default # Note: this may be the object, not the key
                             # associated with a default (if there is any, there
                             # might not be).

    def default( self, ctxt ):
        if self._default is None:
            if verbosity >= 1:
                logger.info("resolver: no default page set")
            # no default page submitted, indicate error
            response.error(response.code.NotFound)
        else:
            # we have a default name, call ourselves again to fetch it
            if type(self._default) in types.StringTypes:
                # default is a string, call ourselves recursively (for the last
                # time)
                ctxt.locator.path.append(self._default)
                return self.handle(ctxt)
            else:
                # default is a Resource, call it directly.
                assert isinstance(self._default, Resource)
                self._default.handle(ctxt)

class FolderWithMenu(Folder):
    """
    A folder resource handler who can render a default page that lists and
    allows access to all the subresources it contains.
    """
    def genmenu( self, ctxt ):
        from htmlout import UL, LI, P, A
        ul = UL()
        for c in sorted(self.iterkeys()):
            path = join(ctxt.locator.uri(), c)
            ul.append( LI(A(c, href=path)) )
        return ul

    def default( self, ctxt ):
        """
        Render a very simple list of the contents of this page.
        """
        # If we have set a default, use it.
        if self._default is not None:
            return Folder.default(self, ctxt)

        from htmlout import HTML, HEAD, BODY, H1, tostring
        menu = self.genmenu(ctxt)
        doc = HTML( HEAD(), BODY(
            H1('Subresources:'), menu
            ))
        response.write(tostring(doc))


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
            logger.info("resolver: %s" % ctxt.locator.path[ctxt.locator.index:])
        if ctxt.locator.isleaf():
            # no username specified
            response.error(response.code.NotFound)

        username = ctxt.locator.current()
        try:
            ctxt.user = self.users[username]
        except KeyError:
            response.error(response.code.NotFound)

        ctxt.locator.next()
        return self.resource.handle(ctxt)


#-------------------------------------------------------------------------------
#
class LeafPage(Resource):
    def handle( self, ctxt ):
        if not ctxt.locator.isleaf():
            response.error(response.code.NotFound)


