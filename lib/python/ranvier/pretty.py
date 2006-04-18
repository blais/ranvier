#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Pretty printing the mapper contents.
"""

# stdlib imports
import StringIO


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


#-------------------------------------------------------------------------------
#
def pretty_render_mapper_body( mapper ):
    """
    Pretty-render just the body for the page that describes the contents of the
    mapper.
    """
    oss = StringIO.StringIO()
    oss.write('<h1>URL Mapper Resources</h1>\n')
    mappings = list(mapper.itervalues())
    mappings.sort(key=lambda x: x.resid)
    for o in mappings:
        # Prettify the URL somewhat for user readability.
        url = mapper.mapurl_tmpl(o.resid, '(<i>%s</i>)')

        # Make the URL clickable if it contains no parameters.
        if not o.defdict:
            url = '<a href="%s">%s</a>' % (url, url)

        m = {'resid': o.resid,
             'url': url}
        oss.write('''
  <h2 class="resource-title"><tt>%(resid)s: %(url)s</tt></h2>
''' % m)
        if o.resource and o.resource.__doc__:
            oss.write('  <p class="docstring">%s</p>' % o.resource.__doc__)
    return oss.getvalue()

