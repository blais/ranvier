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
from ranvier import rodict, RanvierError
from ranvier.resource import Resource
from ranvier.miscres import LeafResource


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
        self.branchs = []
        """A list of the possible branchs for a specific resource node.  This
        list takes on the form of a triple of (type, resource, arg), where arg
        is either None, a fixed component of a variable name depending on the
        type of the branch."""

        self.leaf = None
        """Flag that indicates if the visited node can be served as a leaf."""

        self.leaf_var = None
        """Variable for the leaf, if any."""


    def _add_branch( self, kind, delegate, arg ):
        if not isinstance(delegate, Resource):
            raise RanvierError("Delegate %s must be derived from Resource." %
                               delegate)
        self.branchs.append( (kind, delegate, arg) )

    # Each of the three following functions declares an individual branch of the
    # resource tree.

    def declare_serve( self, varname=None, default=None ):
        """
        Declare that the given resource may serve the contents (at this point in
        the path).  'varname' can be used to declare that it consumes some path
        components as well (optional).
        """
        assert not self.leaf
        self.leaf = True
        if varname is not None:
            self.leaf_var = (varname, default)

    def branch_anon( self, delegate ):
        """
        Declare an anonymous delegate branch.
        """
        self._add_branch(Enumerator.BR_ANONYMOUS, delegate, None)

    def branch_static( self, component, delegate ):
        """
        Declare the consumption of a fixed component of the locator to a
        delegate branch.
        """
        self._add_branch(Enumerator.BR_STATIC, delegate, component)

    def branch_var( self, varname, delegate, default=None ):
        """
        Declare a variable component delegate.  This is used if your resource
        consumes a variable path of the locator.
        """
        self._add_branch(Enumerator.BR_VARIABLE, delegate, (varname, default))

    def get_branches( self ):
        """
        Accessor for branches.
        """
        return self.branchs

    def isleaf( self ):
        """
        Returns true if the visited node has declared itself a leaf.
        """
        return self.leaf


class Enumerator(object):
    """
    A class used to visit and enumerate all the possible URL paths that are
    served by a resource tree.
    """
    BR_ANONYMOUS, BR_STATIC, BR_VARIABLE = xrange(3)
    """Delegate types."""

    def __init__( self ):
        self.accpaths = []
        """The entire list of accumulated paths resulting from the traversal."""

    def visit_root( self, resource ):
        return self.visit(resource, [], 0)

    def visit( self, resource, path, level ):
        """
        Visit a resource node.  This method calls itself recursively.
        * 'resources' is the resource node to visit.
        * 'path' is the current path of components and variables that this
          visitor is currently at.
        """
        # Visit the resource and let it declare the properties of its
        # propagation/search.
        visitor = EnumVisitor()
        resource.enum(visitor)

        # If we have reached a leaf node (i.e. the node has declared itself a
        # potential leaf), add the path to the list of paths.
        if visitor.isleaf():
            if visitor.leaf_var:
                # Append a path with a variable component at the end.
                path = path + [(Enumerator.BR_VARIABLE, None, visitor.leaf_var)]
                self.accpaths.append(path)
            else:
                self.accpaths.append(list(path))

        # Process the possible paths.  This is a breadth-first search.
        branches = visitor.get_branches()
        for branch in branches:
            kind, delegate, arg = branch
            self.visit(delegate, path + [branch], level+1)

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
    def __init__( self, resource_root=None, namexform=None, rootloc=None ):
        rodict.ReadOnlyDict.__init__(self)

        self.rootloc = rootloc
        """A root directory to which the resource tree being handled is
        appended."""

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
            last_resource = root

            for kind, resource, arg in path:
                # Keep a reference to the last resource.
                if resource is not None:
                    last_resource = resource

                # Build the URL string.
                if kind is Enumerator.BR_ANONYMOUS:
                    continue

                elif kind is Enumerator.BR_STATIC:
                    components.append(arg)

                elif kind is Enumerator.BR_VARIABLE:
                    varname, vardef = arg
                    defaults_dict[varname] = vardef
                    components.append('%%(%s)s' % varname)

            # Calculate the resource-id from the resource at the leaf.
            resid = last_resource.getresid(self)

            # Check that the resource-id has not already been seen.
            if resid in self.mappings:
                raise RanvierError("Error: Duplicate resource id '%s'." % resid)

            # Add the mapping.
            self.mappings[resid] = ('/'.join(components),
                                    defaults_dict,
                                    last_resource)

    def _get_url( self, res ):
        """
        Get the URL string and defaults dict for a resource-id, supporting all
        the types described in url().
        """
        # Support passing in resource instances and resource classes as well.
        if isinstance(res, Resource):
            resid = res.getresid(self)
        elif isinstance(res, type) and issubclass(res, Resource):
            resid = self.namexform(res.__name__)
        else:
            resid = res
            assert isinstance(res, (str, unicode))

        # Get the desired mapping.
        try:
            urlstr, defdict, resobj = self.mappings[resid]
        except KeyError:
            raise RanvierError("Error: invalid resource-id '%s'." % resid)
        
        return resid, urlstr, defdict, resobj

    def _subst_url( self, urlstr, params ):
        """
        Substitute the parameters in the URL string and build and return the
        final URL.
        """
        mapped_url = urlstr % params
        return '/'.join((self.rootloc or '', mapped_url))

    def url( self, res, **kwds ):
        """
        Map a resource-id to its URL, filling in the parameters and making sure
        that they are valid.  The keyword arguments are expected to match the
        required arguments for the URL exactly.  The resource id can be either

        1. a string of the class
        2. the class object of the resource (if there is only one of them
           instanced in the tree)
        3. the instance of the resource
        """
        resid, urlstr, defdict, resobj = self._get_url(res)

        # Prepare the defaults dict with the provided values.
        params = defdict.copy()
        for cname, cvalue in kwds.iteritems():
            # Check all provided values are legal.
            if cname not in params:
                raise RanvierError(
                    "Error: '%s' is not a valid component key for mapping the "
                    "'%s' resource.'" % (cname, resid))
            params[cname] = cvalue

        # Check that all the required values have been provided.
        missing = [cname for cname, cvalue in params.iteritems()
                   if cvalue is None]

        if missing:
            raise RanvierError(
                "Error: Missing values attempting to map to a resource: %s" %
                ', '.join(missing))

        return self._subst_url(urlstr, params)
        
    def url_tmpl( self, res, format='%s' ):
        """
        Same as url() above, except that instead of replacing the required
        parameters with supplied values, we replace them with their own name.
        This is used for rendering a readable version of the resources.
        """
        resid, urlstr, defdict, resobj = self._get_url(res)

        # Prepare the defaults dict with the provided values.
        params = dict((x, format % x) for x in defdict.iterkeys())

        return self._subst_url(urlstr, params)

    def getmappings( self ):
        """
        Return an inverse mapping of (url, resid, defdict) triples sorted by
        URL.
        """
        class ResContainer: pass
        mappings = []
        for resid, (url, defdict, resobj) in self.iteritems():
            o = ResContainer()
            o.resid = resid
            o.url = url
            o.defdict = defdict
            o.resobj = resobj
            mappings.append(o)
        mappings.sort(key=lambda x: x.url)
        return mappings

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
        invmap = self.getmappings()

        # Format for alignment for nice printing (and this does make the parsing
        # any more complicated.
        if invmap:
            maxidlen = max(len(x.resid) for x in invmap)
        else:
            maxidlen = 0
        fmt = '%%-%ds : /%%s' % maxidlen

        return [fmt % (o.resid, o.url) for o in invmap]

        # Note: we are considering whether rendering the defaults-dict would be
        # interesting for reconstructing the UrlMapper from a list of lines, as
        # would be done for generating test cases.  For now we ignore the
        # defdict.


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
class EnumResource(LeafResource):
    """
    Enumerate all the resources available from a resource tree.
    """
    def __init__( self, mapper, **kwds ):
        Resource.__init__(self, **kwds)
        self.mapper = mapper

    def handle( self, ctxt ):
        ctxt.response.setContentType('text/plain')
        for line in self.mapper.render():
            ctxt.response.write(line)
            ctxt.response.write('\n')

#-------------------------------------------------------------------------------
#
def pretty_render_mapper( mapper ):
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
body { font-size: smaller }
.resource-title { white-space: nowrap; }
p.docstring { margin-left: 2em; }
--></style>
 <body>
''')

    oss.write(pretty_render_mapper_body(mapper))

    oss.write('''
 </body>
</html>
''')
    return oss.getvalue()


def pretty_render_mapper_body( mapper ):
    """
    Pretty-render just the body for the page that describes the contents of the
    mapper.
    """
    oss = StringIO.StringIO()
    oss.write('<h1>URL Mapper Resources</h1>\n')
    for o in mapper.getmappings():
        # Prettify the URL somewhat for user readability.
        url = mapper.url_tmpl(o.resid, '[<i>%s</i>]')

        # Make the URL clickable if it contains no parameters.
        if not o.defdict:
            url = '<a href="%s">%s</a>' % (url, url)

        m = {'resid': o.resid,
             'url': url}
        oss.write('''
  <h2 class="resource-title"><tt>%(resid)s: %(url)s</tt></h2>
''' % m)
        if o.resobj.__doc__:
            oss.write('  <p class="docstring">%s</p>' % o.resobj.__doc__)
    return oss.getvalue()

