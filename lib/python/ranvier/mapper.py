#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
URL mapper and enumerator classes.
"""

# stdlib imports
import sys, string, StringIO
from os.path import join, normpath
import types

# ranvier imports
import rodict

# hume imports
from hume import response


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
class UrlMapper(rodict.ReadOnlyDict):
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
        rodict.ReadOnlyDict.__init__(self)

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

