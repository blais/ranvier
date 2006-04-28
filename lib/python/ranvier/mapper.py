#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
URL mapper and enumerator classes.
"""

# stdlib imports
import __builtin__, os, re, types, copy, urllib, urlparse

# ranvier imports
from ranvier import rodict, RanvierError, respproxy
from ranvier.resource import Resource
from ranvier.miscres import LeafResource
from ranvier.context import HandlerContext, InternalRedirect
from ranvier.enumerator import Enumerator


__all__ = ['UrlMapper', 'EnumResource']


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
    def __init__( self, root_resource=None, namexform=None, rootloc=None,
                  render_trailing=True ):
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

        self.render_trailing = render_trailing
        """If this is true, automatically render a trailing slash for resources
        that are not leafs."""

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

        for path, isterminal in enumrator.getpaths():
            # Compute the URL string and a dictionary with the defaults.
            # Defaults that are unset are left to None.
            components = []
            last_resource = root_resource

            for kind, resource, arg in path:
                # Keep a reference to the last resource.
                if resource is not None:
                    last_resource = resource

                # Build the URL string.
                if kind is Enumerator.BR_ANONYMOUS:
                    continue

                elif kind is Enumerator.BR_FIXED:
                    components.append( (arg, False, None, None) )

                elif kind is Enumerator.BR_VARIABLE:
                    varname, vardef, varformat = arg

                    if varformat and varformat.startswith('%'):
                        varformat = varformat[1:]

                    components.append( (varname, True, vardef, varformat) )

            # Calculate the resource-id from the resource at the leaf.
            resid = last_resource.getresid(self)

            # Mappings provided by the resource tree are always relative to the
            # rootloc.
            absolute = None

            unparsed = ('', '', absolute, components, '', '')
            mapping = Mapping(resid, unparsed, isterminal, last_resource)
            self._add_mapping(mapping)

    def inject_builtins( self, mapname=None ):
        """
        Inject some variables into the builtins namespace for global access.  It
        makes it possible to access the backward mapping function everywhere in
        a single process by invoking the global functions, which only works for
        a single mapper instance (and that is not a problem in general, since we
        pretty much never need more than one mapper in a running application).

        Warning: this is a useful kludge, but it is nevertheless a kludge.  Know
        what you are doing.
        """
        mapname = mapname or 'mapurl'
        __builtin__.__dict__[mapname] = self.mapurl

    def _add_mapping( self, mapping ):
        """
        Add the given mapping, check for uniqueness.
        """
        resid = mapping.resid

        # Check that the resource-id has not already been seen.
        if resid in self.mappings:
            lines = ("Error: Duplicate resource id '%s':" % resid,
                     "  Existing mapping: %s" %
                     self.mappings[resid].render_pattern(self.rootloc),
                     "  New mapping     : %s" %
                     mapping.render_pattern(self.rootloc))
            raise RanvierError(os.linesep.join(lines))

        # Store the mapping.
        self.mappings[resid] = mapping

    def add_static( self, resid, urlpattern, defaults=None ):
        """
        Add a static URL mapping from 'resid' to the given URL pattern.  This
        may be an external mapping.  The root location will only be prepended to
        the resulting mapping if the pattern is a relative path name (i.e. it
        does not start with '/').  See urlpattern_to_components() for more
        details.
        """
        assert isinstance(resid, str)
        defaults = defaults or {}

        # Parse the URL pattern.
        unparsed, isterminal = urlpattern_to_components(urlpattern, defaults)

        # Add the mapping.
        mapping = Mapping(resid, unparsed, isterminal)
        self._add_mapping(mapping)

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
        self._add_mapping(new_mapping)

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

    def _get_mapping( self, res ):
        """
        Get the mapping for a particular resource-id.
        """
        resid = self.getresid(res)

        # Get the desired mapping.
        try:
            mapping = self.mappings[resid]
        except KeyError:
            raise RanvierError("Error: invalid resource-id '%s'." % resid)

        return mapping

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
        mapping = self._get_mapping(resid)

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
                "Error: Missing values attempting to map resource '%s': %s" %
                (resid, ', '.join("'%s'" % x for x in missing)))

        # Register the target in the call graph, if enabled.
        if self.callgraph_reporter:
            self.callgraph_reporter.register_target(resid)

        # Perform the substitution.
        return mapping.render(params, self.rootloc)

    def mapurl_pattern( self, resid ):
        """
        Same as mapurl() above, except that instead of replacing the required
        parameters with supplied values, we replace them with their own name.
        This is used for rendering a readable version of the resources.
        """
        mapping = self._get_mapping(resid)
        return mapping.render_pattern(self.rootloc)

    def url_variables( self, resid ):
        """
        Returns a tuple of URL variables for a specific resource-id.
        This is some form of introspection on the URLs.
        This can be useful for a test program.
        """
        mapping = self._get_mapping(resid)
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
        fmt = '%%-%ds : %%s' % maxidlen
        
        return [fmt % (m.resid, m.render_pattern(self.rootloc))
                for m in mappings]

        # Note: we are considering whether rendering the defaults-dict would be
        # interesting for reconstructing the UrlMapper from a list of lines, as
        # would be done for generating test cases.  For now we ignore the
        # defdict.

    @staticmethod
    def urlload( url ):
        """
        Load and create a URL mapper by fetching the specified url via the
        network.
        """
        try:
            enumres_text = urllib.urlopen(url).read()
        except IOError:
            raise RanvierError(
                "Error: Fetching contents of mapper from URL '%s'." % url)

        return UrlMapper.load(enumres_text.splitlines())


    @staticmethod
    def load( lines ):
        """
        Load and create URL mapper from the given set of rendered lines.
        See render() for more details.
        """
        mapper = UrlMapper()
        inpat_re = re.compile('([^:\s]+)\s*:\s*(.*)\s*$')

        for line in lines:
            if not line:
                continue

            # Split the id and urlpattern.
            try:
                mo = inpat_re.match(line.strip())
                if not mo:
                    raise ValueError
                resid, urlpattern = mo.groups()
            except ValueError:
                raise RanvierError("Warning: Error parsing line '%s' on load." %
                                   line)
            
            # Note: we do not have defaults when loading from the rendered
            # representation.

            # Parse the loaded line.
            unparsed, isterminal = urlpattern_to_components(urlpattern)

            # Create and add the new mapping.
            mapping = Mapping(resid, unparsed, isterminal)
            mapper._add_mapping(mapping)

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

    def get_match_regexp( self, resid ):
        """
        Return a regular expression to match the URL for the given resource-id.
        """
        mapping = self._get_mapping(resid)
        restring = mapping.render_regexp_matcher(self.rootloc)

        # Note: we do not match the beginning and end because this might be used
        # to match links within a document (e.g. in some test).
        mre = re.compile(restring)
        return mre
    
    def match( self, resid, url ):
        """
        Attempt to match the given URL to the pattern that resid produces.  On
        success return a dictionary of the matched values, where the keys are
        the variable names and the values the matched components of the URL.  On
        failure, return None.

        Important note: this ignores the hostname in the given url and anything
        other than the path.
        """
        # Get the mapping and build a regexp for matching.
        mapping = self._get_mapping(resid)
        restring = mapping.render_regexp_matcher(self.rootloc)
        mre = re.compile('^%s$' % restring)

        # Match against just the given path.
        scheme, netloc, path, query, frag = urlparse.urlsplit(url)
        mo = mre.match(path)
        if not mo:
            return None
        else:
            # Convert the match to the target type, guessed using the format.
            results = {}
            for name, value in zip(mapping.positional, mo.groups()):
                format = mapping.formats.get(name)
                if format and format.endswith('d'):
                    value = int(value)
                elif format and format.endswith('f'):
                    value = float(value)
                results[name] = value

        return results


#-------------------------------------------------------------------------------
#
class Mapping(object):
    """
    Internal class used for storing mappings.
    """
    def __init__( self, resid, unparsed, isterminal, resobj=None ):
        """
        'unparsed' is a tuple of ::

          (scheme, netloc, absolute -> bool, components, query, fragment).

        Otherwise it is None and means that this is a relative mapping.
        See urlpattern_to_components() for a description of the components list.
        """
        # Unpack and store the prefix/suffix for later
        scheme, netloc, absolute, components, query, fragment = unparsed
        self.prefix = scheme, netloc
        self.suffix = query, fragment

        # Whether the path is relative to the mapper's rootloc or absolute
        # (without or outside of this site).
        self.absolute = absolute

        # The list of components
        self.components = components

        # Resource-id and resource object (if specified)
        self.resid = resid
        self.resource = resobj

        # True if this resource does not have any further branches
        self.isterminal = isterminal

        #
        # Pre-calculate stuff for faster backmapping when rendering pages.
        #

        # Build a usable URL string template.
        self.urltmpl, self.urltmpl_untyped = self.create_path_templates()

        # Get positional args, defaults and formats dicts.
        positional, defdict, formats = [], {}, {}
        for name, var, default, format in components:
            if var:
                # Check for variable collisions.
                if name in defdict:
                    raise RanvierError("Variable name collision in URI path.")

                positional.append(name)
                defdict[name] = default
                formats[name] = format

        # A list of the positional variable components, in order.
        self.positional = positional

        # A dictionary for defaults and formats.  All variable names are
        # present, values are set to None if unset.
        self.defdict = defdict
        self.formats = formats

    def create_path_templates( self ):
        """
        Render a string template that can be used with a mapping to perform the
        final rendering.  This returns two formatting strings: one contains
        spaces with the target types, and one that contains generic string
        types.
        """
        rcomps, rcomps_untyped = [], []
        for name, var, default, format in self.components:
            if var:
                if format:
                    repl = '%%(%s)%s' % (name, format)
                    repl_untyped = '%%(%s)s' % name # ignore format
                else:
                    repl = '%%(%s)s' % name
                    repl_untyped = repl
                rcomps.append(repl)
                rcomps_untyped.append(repl_untyped)
            else:
                rcomps.append(name)
                rcomps_untyped.append(name)
        return '/'.join(rcomps), '/'.join(rcomps_untyped)

    def render( self, params, rootloc=None ):
        return self._render(self.urltmpl, params, rootloc)

    def render_pattern( self, rootloc=None ):
        """
        Render the URL pattern using the given params.
        """
        params = {}
        for name, var, default, format in self.components:
            if var:
                if format:
                    repl = '(%s%%%s)' % (name, format)
                else:
                    repl = '(%s)' % name
                params[name] = repl

        return self._render(self.urltmpl_untyped, params, rootloc)

    def render_regexp_matcher( self, rootloc=None ):
        """
        Render a regular expression string for matching against a known URL.
        """
        params = {}
        for name, var, default, format in self.components:
            if var:
                if format is None or format.endswith('s'):
                    params[name] = '(?P<%s>[^/]+)' % name
                elif format.endswith('d'):
                    params[name] = '(?P<%s>[0-9]+)' % name
                elif format.endswith('f'):
                    params[name] = '(?P<%s>[0-9\\.\\+\\-]+)' % name

        restring = self._render(self.urltmpl_untyped, params, rootloc)
        if restring.endswith('/'):
            restring += '?'
        else:
            restring += '/?'
        return restring

    def _render( self, template, params, rootloc=None, render_trailing=True ):
        """
        Render the final URL using the given params.  The dict should exactly
        match the variables in the template.
        """
        rendered_path = template % params
        if self.absolute:
            first_comp = ''
        else:
            first_comp = rootloc or ''
        rendered_path = '/'.join((first_comp, rendered_path))

        # Add a trailing slash if the resource if not a leaf
        if render_trailing and self.isterminal:
            if not rendered_path.endswith('/'):
                rendered_path += '/'

        unparsed = self.prefix + (rendered_path,) + self.suffix

        return urlparse.urlunsplit(unparsed)


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
compre = re.compile('^\\(([a-z]+)(?:%([a-z0-9\\-]+))?\\)$')

def urlpattern_to_components( urlpattern, defaults=None ):
    """
    Convert a URL pattern string to a list of components.  Return a tuple of

      (scheme, netloc, absolute, list of components, query, fragment).

    The list of components consists of

       (name -> str, var -> bool, default -> str|None, format -> str|None)

    tuples.  Default values can be specified via 'defaults' if given, until we
    can add enough to the URL pattern format to provide this.

    Note: We determine solely from the URL pattern whether it is a relative
    vs. absolute path, and we do this here, e.g.::

       http://domain.com/gizmos         : external link
       /gizmos                          : absolute link
       gizmos                           : relative link

    Relative URLs are always considered to be relative to the root of the
    mapper, and not relative to each other, folder, etc.  Normally, the only
    relative mappings are those from the resource tree.  When we render out the
    mappings, however, they are always absolute.

    The format of the variable components is a parenthesized name, e.g.::

         /users/(username)/mygizmos

    You can specify a format for producing URLs for specific components::

         /catalog/gizmos/(id%08d)

    """
    scheme, netloc, path, query, fragment = urlparse.urlsplit(urlpattern)

    # Find out if the URL we're trying to map is absolute.
    absolute = scheme or netloc or path.startswith('/')

    # Remove the prepending slash for splitting the components.
    if path.startswith('/'):
        path = path[1:]

    # Find out if this is a terminal and remove the extra slash.
    isterminal = path.endswith('/')
    if isterminal:
        path = path[:-1]

    # Parse the URL pattern.
    components = []
    indefs = defaults and defaults.copy() or {}

    for comp in path.split('/'):
        mo = compre.match(comp)
        if not mo:
            # Catch components with parentheses that are misformed.
            if ')' in comp or '(' in comp:
                raise RanvierError(
                    "Error: Invalid component in static mapping '%s'." %
                    urlpattern)

            # Add a fixed component
            components.append( (comp, False, None, None) )
            continue
        else:
            varname, varformat = mo.group(1, 2)
            vardef = indefs.pop(varname, None)
            components.append( (varname, True, vardef, varformat) )

    # Check that the provided defaults are all valid (i.e. there is not a
    # default that does not match a variable in the given URL pattern).
    if indefs:
        raise RanvierError(
            "Error: invalid extra defaults for given URL pattern.")

    return (scheme, netloc, absolute, components, query, fragment), isterminal


#-------------------------------------------------------------------------------
#
class EnumResource(LeafResource):
    """
    Enumerate all the resources available from a resource tree.
    """
    def __init__( self, mapper, **kwds ):
        LeafResource.__init__(self, **kwds)
        self.mapper = mapper

    def handle( self, ctxt ):
        ctxt.response.setContentType('text/plain')
        for line in self.mapper.render():
            ctxt.response.write(line)
            ctxt.response.write('\n')

