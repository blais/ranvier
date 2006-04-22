#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
URL mapper and enumerator classes.
"""

# stdlib imports
import sys, os, string, StringIO, re, types, copy
from os.path import join, normpath

# ranvier imports
from ranvier import rodict, RanvierError, respproxy
from ranvier.resource import Resource
from ranvier.miscres import LeafResource
from ranvier.context import HandlerContext, InternalRedirect
from ranvier.enumerator import Enumerator


__all__ = ['UrlMapper', 'EnumResource']


#-------------------------------------------------------------------------------
#
compre = re.compile('^\\(([a-z]+?)\\)$')

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
    def __init__( self, root_resource=None, namexform=None, rootloc=None ):
        rodict.ReadOnlyDict.__init__(self)

        self.root_resource = root_resource
        """The root resource to start mapping forward from."""

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

        self.callgraph_reporter = None
        """An object used to log inter-resource references in order to produce a
        call graph."""

        if root_resource is not None:
            self.initialize(root_resource)

    def initialize( self, root_resource ):
        """
        Add the resource from the given root to the current mapper.  You need to
        call this at least once before using the mapper to fill it with some
        values, and with resources at the same resource level.
        """
        assert root_resource
        self.root_resource = root_resource

        enumrator = Enumerator()
        enumrator.visit_root(root_resource)

        for path in enumrator.getpaths():
            # Compute the URL string and a dictionary with the defaults.
            # Defaults that are unset are left to None.
            components = []
            positional = []
            defaults_dict = {}
            last_resource = root_resource

            for kind, resource, arg in path:
                # Keep a reference to the last resource.
                if resource is not None:
                    last_resource = resource

                # Build the URL string.
                if kind is Enumerator.BR_ANONYMOUS:
                    continue

                elif kind is Enumerator.BR_FIXED:
                    components.append(arg)

                elif kind is Enumerator.BR_VARIABLE:
                    varname, vardef = arg

                    # Check for variable collisions.
                    if varname in defaults_dict:
                        raise RanvierError(
                            "Variable name collision in URI path.")

                    defaults_dict[varname] = vardef
                    positional.append(varname)
                    components.append('(%s)' % varname)

            # Calculate the resource-id from the resource at the leaf.
            resid = last_resource.getresid(self)

            # Mappings provided by the resource tree are always relative to the
            # rootloc.
            absolute = False

            mapping = Mapping(resid,
                              '/'.join(components),
                              defaults_dict,
                              positional,
                              absolute,
                              last_resource)
            self._add_mapping(resid, mapping)

    def _add_mapping( self, resid, mapping ):
        """
        Add the given mapping, check for uniqueness.
        """
        # Check that the resource-id has not already been seen.
        if resid in self.mappings:
            lines = ("Error: Duplicate resource id '%s':" % resid,
                     "  Existing mapping: %s" % self.mappings[resid].urlpattern,
                     "  New mapping     : %s" % mapping.urlpattern)
            raise RanvierError(os.linesep.join(lines))

        # Store the mapping.
        self.mappings[resid] = mapping

    def add_static( self, resid, urlpattern, defaults={} ):
        """
        Add a static URL mapping from 'resid' to the given URL pattern.  This
        may be an external mapping.  The rootlocation will only be prepended to
        the resulting mapping if the pattern is a relative path name (i.e. it
        does not start with '/').

        'urlpattern' is a string that may contain parenthesized expressions to
        declare variable component names, for example::

            http://mycatalog.com/book/(isbn)/comments

        This declares a mapping where 'isbn' will be a required argument to
        produce the mapping.
        """
        assert isinstance(resid, str)

        # Find out if the URL we're trying to map is absolute
        absolute = urlpattern.startswith('/') or '://' in urlpattern

        # Parse the URL pattern.
        components = []
        positional = []
        defaultsc, defaults_dict = defaults.copy(), {}

        for comp in urlpattern.split('/'):
            mo = compre.match(comp)
            if mo:
                varname = mo.group(1)

                # Check for variable collisions.
                if varname in defaults_dict:
                    raise RanvierError(
                        "Variable name collision in URI path.")

                defaults_dict[varname] = defaultsc.pop(varname, None)
                positional.append(varname)
                components.append('(%s)' % varname)
            else:
                if ')' in comp or '(' in comp:
                    raise RanvierError(
                        "Error: Invalid component in static mapping '%s'." %
                        urlpattern)
                components.append(comp)

        # Check that the provided defaults are all valid (i.e. there is no a
        # default that does not match a variable in the given URL pattern).
        if defaultsc:
            raise RanvierError(
                "Error: invalid defaults for given URL pattern.")

        # Add the mapping.
        mapping = Mapping(resid,
                          '/'.join(components),
                          defaults_dict,
                          positional,
                          absolute)
        self._add_mapping(resid, mapping)

    def add_alias( self, new_resid, existing_resid ):
        """
        Add an alias to a mapping, that is, another resource-id which will point
        to the same mapping.  The target mapping must already be existing.
        """
        try:
            mapping = self.mappings[existing_resid]
        except KeyError:
            raise RanvierError(
                "Error: Target mapping '%s' must exist for alias '%s'." %
                (existing_resid, new_resid))
        
        new_mapping = copy.copy(mapping)
        new_mapping.resid = new_resid
        self._add_mapping(new_resid, new_mapping)

    def getresid( self, res ):
        """
        Get a resource-id, supporting all the types described in mapurl().
        """
        # Support passing in resource instances and resource classes as well.
        if isinstance(res, Resource):
            resid = res.getresid(self)
        elif isinstance(res, type) and issubclass(res, Resource):
            resid = self.namexform(res.__name__)
        else:
            resid = res
            assert isinstance(res, (str, unicode))
        return resid
        
    def _get_url( self, res ):
        """
        Get the URL string and defaults dict for a 
        """
        resid = self.getresid(res)

        # Get the desired mapping.
        try:
            mapping = self.mappings[resid]
        except KeyError:
            raise RanvierError("Error: invalid resource-id '%s'." % resid)

        return mapping

    def _substitute( self, urltmpl, params, absolute ):
        """
        Substitute the parameters in the URL string and build and return the
        final URL.
        """
        mapped_url = urltmpl % params
        if absolute:
            return mapped_url
        else:
            return '/'.join((self.rootloc or '', mapped_url))

    def mapurl( self, resid, *args, **kwds ):
        """
        Map a resource-id to its URL, filling in the parameters and making sure
        that they are valid.  The keyword arguments are expected to match the
        required arguments for the URL exactly.  The resource id can be either

        1. a string of the class
        2. the class object of the resource (if there is only one of them
           instanced in the tree)
        3. the instance of the resource

        Positional arguments can be used as well, and they are used to fill in
        the URL string with the missing components, in left-to-right order (root
        to leaf).

        Alternatively, if a **single** positional argument is provided and it is
        **an instance or a dict type**, we will fetch the attributes/values from
        this object to fill in the missing values.  You can combine this with
        keyword arguments as well.
        """
        mapping = self._get_url(resid)

        # Check for an instance or dict to fetch some positional args from.
        if len(args) == 1 and not isinstance(args[0],
                                             (str, unicode, int, long)):
            dicmissing = args[0]
            if not isinstance(dicmissing, dict):
                # Then we must have hold of a user defined class.
                dicmissing = dicmissing.__dict__
        else:
            # Normal positional arguments are integrated with the keyword
            # arguments..
            dicmissing = None
            nbpos = len(mapping.positional)
            if len(args) > nbpos:
                raise RanvierError("Error: Resource '%s' takes at most '%d' "
                                   "arguments." % (mapping.resid, nbpos))

            for posname, posarg in zip(mapping.positional, args):
                if posname in kwds:
                    raise RanvierError(
                        "Error: Creating URL for '%s', got multiple "
                        "values for component '%s'." % (mapping.resid, posname))
                kwds[posname] = posarg

        # Get a copy of the defaults.
        params = mapping.defdict.copy()

        # Attempt to fill in the missing values from the object or dict, if one
        # was given.  We do this before integrating the keywords, because we
        # want the keywords to have priority and override the dict/object
        # values if they are present in both.
        if dicmissing is not None:
            for cname, cvalue in params.iteritems():
                if cvalue is None:
                    try:
                        params[cname] = dicmissing[cname]
                    except KeyError:
                        pass

        # Override the defaults dict with the provided values.
        for cname, cvalue in kwds.iteritems():
            # Check all provided values are legal.
            if cname not in params:
                raise RanvierError(
                    "Error: '%s' is not a valid component key for mapping the "
                    "'%s' resource.'" % (cname, mapping.resid))

            # Fill the slot with the specified value
            params[cname] = cvalue
                    
        # Check that all the required values have been provided.
        missing = [cname for cname, cvalue in params.iteritems()
                   if cvalue is None]

        if missing:
            raise RanvierError(
                "Error: Missing values attempting to map to a resource: %s" %
                ', '.join("'%s'" % x for x in missing))
    
        # Register the target in the call graph, if enabled.
        if self.callgraph_reporter:
            self.callgraph_reporter.register_target(resid)

        # Perform the substitution.
        return self._substitute(mapping.urltmpl, params, mapping.absolute)

    def mapurl_tmpl( self, resid, format='%s' ):
        """
        Same as mapurl() above, except that instead of replacing the required
        parameters with supplied values, we replace them with their own name.
        This is used for rendering a readable version of the resources.
        """
        mapping = self._get_url(resid)

        # Prepare the defaults dict with the provided values.
        params = dict((x, format % x) for x in mapping.defdict.iterkeys())

        return self._substitute(mapping.urltmpl, params, mapping.absolute)

    def url_variables( self, resid ):
        """
        Returns a tuple of URL variables for a specific resource-id.
        This is some form of introspection on the URLs.
        This can be useful for a test program.
        """
        mapping = self._get_url(resid)
        return tuple(mapping.positional)

    def render( self, sort_by_url=True ):
        """
        Render the contents of the mapper so that it can be reconstructed from
        the given text, to be able to create some URLs.  This returns a list of
        lines (str) of output.

        Cool idea: This can be served from a resource (enabled only in test
        mode) on your server, so that the automated tests can use this to
        generate the URLs that they are testing.  This means that you could
        entirely shuffle the URLs in your web application and your entire test
        suite would still keep working.
        """
        mappings = list(self.itervalues())
        if sort_by_url:
            sortfun = lambda x: x.urltmpl
        else:
            sortfun = lambda x: x.resid
        mappings.sort(key=sortfun)
            

        # Format for alignment for nice printing (and this does make the parsing
        # any more complicated.
        if mappings:
            maxidlen = max(len(x.resid) for x in mappings)
        else:
            maxidlen = 0
        fmt = '%%-%ds , %%c , %%s' % maxidlen

        return [fmt % (o.resid, o.absolute and 'A' or 'R', o.urlpattern)
                for o in mappings]

        # Note: we are considering whether rendering the defaults-dict would be
        # interesting for reconstructing the UrlMapper from a list of lines, as
        # would be done for generating test cases.  For now we ignore the
        # defdict.

    @staticmethod
    def load( lines ):
        """
        Load and create URL mapper from the given set of rendered lines.
        See render() for more details.
        """
        ure = re.compile('\\(([a-z]+?)\\)')

        mapper = UrlMapper()

        for line in lines:
            if not line:
                continue
            
            # Split the id and urlpattern.
            try:
                resid, absolute, urlpattern = map(str.strip, line.split(','))
            except ValueError:
                raise RanvierError("Warning: Error parsing line '%s' on load." %
                                   line)

            # Parse the components in the urlpattern.
            positional = ure.findall(urlpattern)

            # Relative or absolute.
            absolute = (absolute == 'A')

            # Defaults dictionary.  Note: the renderer does not provide the
            # defaults yet. We could use a pickle eventually, or whatever.  I
            # simple like readable formats for now.
            defdict = dict((x, None) for x in positional)

            # Add the mapping to the mapper, without the resource handler
            # objects.
            mapping = Mapping(resid, urlpattern, defdict, positional, absolute)
            mapper.mappings[resid] = mapping

        return mapper


    def handle_request( self, uri, args, response_proxy=None, **extra ):
        """
        Handle a request, via the resource tree.  This is the pattern matching /
        forward mapping part.

        'uri': the requested URL, including the rootloc, if present.

        'args': a dict of the arguments (POST or GET variables)

        'response_proxy': an adapter for the resources that Ranvier provides.

        'extra': the extra keyword args are added as attribute to the context
        object that the handlers receive
        """

        if self.root_resource is None:
            raise RanvierError("Error: You need to initialize the mapper with "
                               "a resource to perform forward mapping.")

        assert isinstance(uri, str)
        # assert isinstance(args, dict) # Note: Also allow dict-like interfaces.
        assert isinstance(response_proxy,
                          (types.NoneType, respproxy.ResponseProxy))

        while True:
            # Remove the root location if necessary.
            if self.rootloc is not None:
                if not uri.startswith(self.rootloc):
                    raise RanvierError("Error: Incorrect root location '%s' "
                                       "for requested URI '%s'." %
                                       (self.rootloc, uri))
                uri = uri[len(self.rootloc):]

            # Create a context for the handling.
            ctxt = HandlerContext(uri, args, self.rootloc)

            # Setup the callgraph reporter.
            ctxt.callgraph = self.callgraph_reporter
            ctxt.mapper = self

            # Standard stuff that we graft onto the context object.
            ctxt.response = response_proxy

            # Provide in the context a function to backmap URLs from resource
            # ids.  We should not need more than this, so we try not to provide
            # access to the full mapper to resource handlers, at least not until
            # we really need it.
            ctxt.mapurl = self.mapurl

            # Add extra payload on the context object.
            for aname, avalue in extra.iteritems():
                setattr(ctxt, aname, avalue)

            # Handle the request.
            try:
                self.root_resource.handle_base(ctxt)
                break # Success, break out.
            except InternalRedirect, e:
                uri, args = e.uri, e.args
                # Loop again for the internal redirect.

        if ctxt.callgraph:
            ctxt.callgraph.complete()

    def enable_callgraph( self, reporter ):
        """
        Enable callgraph accumulation.
        """
        self.callgraph_reporter = reporter

    def disable_callgraph( self ):
        self.callgraph_reporter = None

        
#-------------------------------------------------------------------------------
#
class Mapping(object):
    """
    Internal class used for storing mappings.
    """
    def __init__( self, resid, urlpattern, defdict, positional, absolute,
                  resobj=None,  ):
        # Build a usable URL string template.
        urltmpl = urlpattern.replace('(', '%(').replace(')', ')s')

        self.resid = resid
        self.urlpattern = urlpattern
        self.urltmpl = urltmpl
        self.defdict = defdict
        self.positional = positional
        self.resource = resobj
        self.absolute = absolute


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

