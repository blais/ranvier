#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Pretty printing the mapper contents.
"""

# stdlib imports
import StringIO

# ranvier imports
import ranvier.template
from ranvier.miscres import LeafResource


__all__ = ('PrettyEnumResource', 'pretty_render_mapper_body')


#-------------------------------------------------------------------------------
#
class PrettyEnumResource(LeafResource):
    """
    Output a rather nice page that describes all the pages that are being served
    from the given mapper.
    """
    def __init__( self, mapper, sorturls=False, **kwds ):
        """
        If 'sorturls' is True, we sort by URLs and change the rendering
        somewhat.
        """
        LeafResource.__init__(self, **kwds)
        self.mapper = mapper
        self.sorturls = sorturls

    def handle( self, ctxt ):
        ctxt.response.setContentType('text/html')
        ranvier.template.render_header(ctxt.response,
                                       'URL Mapper Resources')

        ctxt.response.write(pretty_render_mapper_body(self.mapper,
                                                      dict(ctxt.args),
                                                      self.sorturls))

        ranvier.template.render_footer(ctxt.response)


#-------------------------------------------------------------------------------
#
def pretty_render_mapper_body( mapper, defaults, sorturls ):
    """
    Pretty-render just the body for the page that describes the contents of the
    mapper.
    """
    # Try to convert the defaults to ints if some are, this won't hurt.
    for name, value in defaults.iteritems():
        try:
            value = int(value)
            defaults[name] = value
        except ValueError:
            pass

    oss = StringIO.StringIO()
    oss.write('<h1>URL Mapper Resources</h1>\n')
    mappings = list(mapper.itervalues())
    if sorturls:
        sortkey = lambda x: x.urltmpl
        titfmt = ('<h2 class="resource-title"><tt>%(url)s</tt> '
                  '(<tt>%(resid)s</tt>)</h2>')
    else:
        sortkey = lambda x: x.resid
        titfmt = '<h2 class="resource-title"><tt>%(resid)s: %(url)s</tt></h2>'
    mappings.sort(key=sortkey)

    for o in mappings:
        # Prettify the URL somewhat for user readability.
        url = mapper.mapurl_pattern(o.resid)

        # Try to fill in missing values from in the defaults dict
        defdict = o.defdict.copy()
        for cname, cvalue in defaults.iteritems():
            if cname in defdict:
                defdict[cname] = cvalue

        # Make the URL clickable if it contains no parameters.
        if None not in defdict.itervalues():
            url = '<a href="%s">%s</a>' % (mapper.mapurl(o.resid, defdict), url)

        m = {'resid': o.resid,
             'url': url}

        oss.write(titfmt % m)
        if o.resource and o.resource.__doc__:
            oss.write('  <p class="docstring">%s</p>' % o.resource.__doc__)
    return oss.getvalue()

