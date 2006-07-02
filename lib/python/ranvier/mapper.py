#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
URL mapper and enumerator classes.
"""

# stdlib imports
import __builtin__, os, re, types, copy, urllib, urlparse
from itertools import chain

# ranvier imports
from ranvier import rodict, RanvierError, respproxy
from ranvier.resource import Resource
from ranvier.miscres import LeafResource
from ranvier.context import HandlerContext, InternalRedirect
from ranvier.enumerator import \
    Enumerator, FixedComponent, VarComponent, OptParam


__all__ = ('UrlMapper', 'EnumResource')


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
    def __init__(self, root_resource=None, rootloc=None,
                 render_trailing=True):
        rodict.ReadOnlyDict.__init__(self)

        self.root_resource = root_resource
        """The root resource to start mapping forward from."""

        self.rootloc = rootloc
        """A root directory to which the resource tree being handled is
        appended."""

        self.mappings = self.rwdict
        """Mappings from resource-id to mapping objects."""

        self.reporters = []
        """A lis of interfaces to reporter objects used to do something each
        time a resource is handled or rendered.  This can be used to
        automatically produce a graph of the relationships between pages, or a
        coverage analysis."""

        self.render_trailing = render_trailing
        """If this is true, automatically render a trailing slash for resources
        that are not leafs."""

        if root_resource is not None:
            self.initialize(root_resource)

    def initialize(self, root_resource):
        """
        Add the resource from the given root to the current mapper.  You need to
        call this at least once before using the mapper to fill it with some
        values, and with resources at the same resource level.
        """
        assert root_resource
        self.root_resource = root_resource

        enumrator = Enumerator()
        enumrator.visit_root(root_resource)

        for (resource, components, optparams,
             isterminal) in enumrator.getpaths():

            # Calculate the resource-id from the resource at the leaf.
            resid = getresid_any(resource)

            # Mappings provided by the resource tree are always relative to the
            # rootloc.
            absolute = None

            unparsed = ('', '', absolute, components, '', '')
            mapping = Mapping(resid, unparsed, isterminal, resource, optparams)

            self._add_mapping(mapping)

    def inject_builtins(self, mapname=None):
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

    def _add_mapping(self, mapping):
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

    def add_static(self, resid, urlpattern):
        """
        Add a static URL mapping from 'resid' to the given URL pattern.  This
        may be an external mapping.  The root location will only be prepended to
        the resulting mapping if the pattern is a relative path name (i.e. it
        does not start with '/').  See urlpattern_to_components() for more
        details.
        """
        assert isinstance(resid, str)

        # Parse the URL pattern.
        unparsed, isterminal = urlpattern_to_components(urlpattern)

        # Add the mapping.
        mapping = Mapping(resid, unparsed, isterminal)
        self._add_mapping(mapping)

    def add_alias(self, new_resid, existing_resid):
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

    def _get_mapping(self, res):
        """
        Get the mapping for a particular resource-id.
        """
        resid = getresid_any(res)

        # Get the desired mapping.
        try:
            mapping = self.mappings[resid]
        except KeyError:
            raise RanvierError("Error: invalid resource-id '%s'." % resid)

        return mapping

    def mapurl(self, resid, *args, **kwds):
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

        # Create a dict of the required positional arguments.
        posargs = mapping.posmap.copy()

        # Check for an instance or dict to fetch some positional args from.
        if len(args) == 1 and not isinstance(args[0],
                                             (str, unicode, int, long)):
            diccontainer = args[0]
            if not isinstance(diccontainer, dict):
                # Then we must have hold of a user defined class.
                diccontainer = diccontainer.__dict__
        else:
            # No dict, instead we have positional arguments.
            diccontainer = {}

            # Check that we don't have extra positional arguments.
            nbpos = len(posargs)
            if len(args) > nbpos:
                raise RanvierError(
                    "Error: Resource '%s' takes at most %d arguments "
                    "(%d given)." % (mapping.resid, nbpos, len(args)))

            # Set the positional arguments.
            for comp, arg in zip(mapping.positional, args):
                posargs[comp.varname] = arg

        # Fill in the missing positional arguments.
        for name, value in posargs.iteritems():
            if value is None:
                # Try to get the name from the keyword arguments.
                try:
                    value = kwds.pop(name)
                except KeyError:
                    # Try to get the name from the container object.
                    try:
                        value = diccontainer[name]
                    except KeyError:
                        raise RanvierError(
                            "Error: Resource '%s' had no value supplied for "
                            "positional argument '%s'" % (mapping.resid, name))

                posargs[name] = value

        # Sanity check.
        if __debug__:
            for value in posargs.itervalues():
                assert value is not None

        # Process the remaining keyword arguments.  They should specify only
        # optional parameters at this point, we should have extracted positional
        # arguments specified as keywords arguments above.
        for name, value in kwds.iteritems():
            if name not in mapping.optparams:
                if name in posargs:
                    raise RanvierError("Error: Resource '%s' got multiple "
                                       "values for optional parameter '%s'" %
                                       (mapping.resid, name))
                else:
                    raise RanvierError("Error: Resource '%s' got an "
                                       "unexpected optional parameter '%s'" %
                                       (mapping.resid, name))
        optargs = kwds

        # Register the target in the call graph, if enabled.
        for rep in self.reporters:
            rep.register_rendered(resid)

        # Perform the substitution.
        return mapping.render(posargs, self.rootloc)

    def mapurl_noerror(self, resid, *args, **kwds):
        """
        Same as mapurl(), except that we just return None if there is an error.
        """
        try:
            return self.mapurl(resid, *args, **kwds)
        except RanvierError:
            return None

    def mapurl_pattern(self, resid):
        """
        Same as mapurl() above, except that instead of replacing the required
        parameters with supplied values, we replace them with their own name.
        This is used for rendering a readable version of the resources.
        """
        mapping = self._get_mapping(resid)
        return mapping.render_pattern(self.rootloc)

    def url_variables(self, resid):
        """
        Returns a tuple of URL variables for a specific resource-id.
        This is some form of introspection on the URLs.
        This can be useful for a test program.
        """
        mapping = self._get_mapping(resid)
        return tuple(x.varname for x in mapping.positional)

    def render(self, sort_by_url=True):
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


    @staticmethod
    def urlload(url):
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
    def load(lines):
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


    def getabsoluteids(self):
        """
        Return a list of the absolute-ids registered with the mapper, which
        cannot never be handled by handle_request() (they are just used for
        rendering external resources, or resources not rooted at the root).
        """
        return [x.resid for x in self.itervalues() if x.absolute]


    def handle_request(self, method, uri, args, response_proxy=None, **extra):
        """
        Handle a request, via the resource tree.  This is the pattern matching /
        forward mapping part.

        'method': the request method, i.e. GET, POST, etc.

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

        redirect_data = None
        while True:
            # Start reporter.
            for rep in self.reporters:
                rep.begin()

            # Remove the root location if necessary.
            if self.rootloc is not None:
                if not uri.startswith(self.rootloc):
                    raise RanvierError("Error: Incorrect root location '%s' "
                                       "for requested URI '%s'." %
                                       (self.rootloc, uri))
                uri = uri[len(self.rootloc):]

            # Create a context for the handling.
            ctxt = HandlerContext(method, uri, args, self.rootloc)
            ctxt.mapper = self

            # Add the redirect data
            ctxt.redirect_data = redirect_data

            # Setup the reporters.
            ctxt.reporters = self.reporters

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
                try:
                    Resource.delegate(self.root_resource, ctxt)
                    break # Success, break out.
                except InternalRedirect, e:
                    redirect_data = e
                    uri, args = e.uri, e.args
                    # Loop again for the internal redirect.
            finally:
                # Complete reporters.
                for rep in self.reporters:
                    rep.end()

    def add_reporter(self, reporter):
        """
        Add the given reporter to the active list.
        """
        self.reporters.append(reporter)

    def remove_reporter(self, reporter):
        """
        Remove the given reporter from the list.  The reporter must have been
        previously added.
        """
        try:
            self.reporters.remove(reporter)
        except IndexError:
            raise RanvierError("Trying to remove an unregistered reporter.")

    def get_match_regexp(self, resid):
        """
        Return a regular expression to match the URL for the given resource-id.
        """
        mapping = self._get_mapping(resid)
        restring = mapping.render_regexp_matcher(self.rootloc)

        # Note: we do not match the beginning and end because this might be used
        # to match links within a document (e.g. in some test).
        mre = re.compile(restring)
        return mre

    def match(self, resid, url):
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
            for comp, value in zip(mapping.positional, mo.groups()):
                format = comp.format
                if format and format.endswith('d'):
                    value = int(value)
                elif format and format.endswith('f'):
                    value = float(value)
                results[comp.varname] = value

        return results


#-------------------------------------------------------------------------------
#
class Mapping(object):
    """
    Internal class used for storing mappings.
    """
    def __init__(self, resid, unparsed, isterminal,
                 resobj=None, optparams=None):
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

        # Set the positional args to the list of components with variables.
        self.positional = filter(lambda x: isinstance(x, VarComponent),
                                 components)
        self.posmap = dict((x.varname, None) for x in self.positional)
        # Note: only exists for efficient copy in mapurl.

        # Check for collisions.  We keep the set around for fast validity
        # checks afterwards.
        varset = set()
        for comp in chain(self.positional, optparams or ()):
            if comp.varname in varset:
                raise RanvierError(
                    "Variable name collision in URI path: '%s'" % comp.varname)
            varset.add(comp.varname)
        self.varset = varset
        # Note: varset includes both the positional and optional parameters.

        # A dict of the optional parameters.
        self.optparams = dict((x.varname, x) for x in optparams or ())

    def create_path_templates(self):
        """
        Render a string template that can be used with a mapping to perform the
        final rendering.  This returns two formatting strings: one contains
        spaces with the target types, and one that contains generic string
        types.
        """
        rcomps, rcomps_untyped = [], []
        for comp in self.components:
            if isinstance(comp, VarComponent):
                if comp.format:
                    repl = '%%(%s)%s' % (comp.varname, comp.format)
                    repl_untyped = '%%(%s)s' % comp.varname # ignore format
                else:
                    repl = '%%(%s)s' % comp.varname
                    repl_untyped = repl
                rcomps.append(repl)
                rcomps_untyped.append(repl_untyped)
            else:
                assert isinstance(comp, FixedComponent)
                rcomps.append(comp.name)
                rcomps_untyped.append(comp.name)
        return '/'.join(rcomps), '/'.join(rcomps_untyped)

    def render(self, posargs, rootloc=None):
        return self._render(self.urltmpl, posargs, rootloc)

    def render_pattern(self, rootloc=None):
        """
        Render the URL pattern using the given posargs.
        """
        posargs = {}
        for comp in self.positional:
            if comp.format:
                repl = '(%s%%%s)' % (comp.varname, comp.format)
            else:
                repl = '(%s)' % comp.varname
            posargs[comp.varname] = repl

        return self._render(self.urltmpl_untyped, posargs, rootloc)

    def render_regexp_matcher(self, rootloc=None):
        """
        Render a regular expression string for matching against a known URL.
        """
        posargs = {}
        for comp in self.positional:
            format = comp.format
            if format is None or format.endswith('s'):
                posargs[comp.varname] = '(?P<%s>[^/]+)' % comp.varname
            elif format.endswith('d'):
                posargs[comp.varname] = '(?P<%s>[0-9]+)' % comp.varname
            elif format.endswith('f'):
                posargs[comp.varname] = '(?P<%s>[0-9\\.\\+\\-]+)' % comp.varname

        restring = self._render(self.urltmpl_untyped, posargs, rootloc)
        if restring.endswith('/'):
            restring += '?'
        else:
            restring += '/?'
        return restring

    def _render(self, template, posargs, rootloc=None, render_trailing=True):
        """
        Render the final URL using the given posargs.  The dict should exactly
        match the variables in the template.
        """
        rendered_path = template % posargs
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

        rendered = urlparse.urlunsplit(unparsed)

        # Render the optional parameters.


## FIXME: todo

        return rendered



#-------------------------------------------------------------------------------
#
def getresid_any(res):
    """
    Get a resource-id.  This static method accepts 'res' being either of

    - a string type (str or unicode)
    - some resource class
    - a resource instance

    This is used to interpret input parameters passed in to the mapper.

    """
    # Support passing in resource instances and resource classes as well.
    if isinstance(res, Resource):
        resid = res.getresid()
    elif isinstance(res, type) and issubclass(res, Resource):
        resid = ranvier._namexform(res.__name__)
    else:
        resid = res
        assert isinstance(res, (str, unicode))
    return resid


#-------------------------------------------------------------------------------
#
compre = re.compile('^\\(([a-z][a-z_]*)(?:%([a-z0-9\\-]+))?\\)$')

def urlpattern_to_components(urlpattern):
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
    components = []  # name, var, format

    for comp in path.split('/'):
        mo = compre.match(comp)
        if not mo:
            # Catch components with parentheses that are misformed.
            if ')' in comp or '(' in comp:
                raise RanvierError(
                    "Error: Invalid component in static mapping '%s'." %
                    urlpattern)

            # Add a fixed component
            components.append( FixedComponent(comp) )
            continue
        else:
            varname, varformat = mo.group(1, 2)
            components.append( VarComponent(varname, varformat) )

    return (scheme, netloc, absolute, components, query, fragment), isterminal


#-------------------------------------------------------------------------------
#
class EnumResource(LeafResource):
    """
    Enumerate all the resources available from a resource tree.
    """
    def __init__(self, mapper, **kwds):
        LeafResource.__init__(self, **kwds)
        self.mapper = mapper

    def handle(self, ctxt):
        ctxt.response.setContentType('text/plain')
        for line in self.mapper.render():
            ctxt.response.write(line)
            ctxt.response.write('\n')


