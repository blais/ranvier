#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Basic HTML template for resources provided by Ranvier that render something.
This is not meant to be exported.  Normally you would probably override the
handle() method of the resources to embed its rendering within your own module's
template.

In case it is not clear, this is NOT meant for you to use, this is only a
convenience template meant to be used only by the few resources provided by this
package.
"""


__all__ = ()


_generator = 'Ranvier URL Mapping Library'


#-------------------------------------------------------------------------------
#
def render_header( oss, title, css='' ):
    """
    Render an HTML page header.
    """
    m = {'generator': _generator,
         'title': title,
         'css': css}
    
    oss.write('''
<html>
  <head>
    <title>%(title)s</title>
    <meta name="generator" content="%(generator)s" />
    <style type="text/css"><!--
body { font-size: smaller }
.resource-title { white-space: nowrap; }
p.docstring { margin-left: 2em; }
%(css)s
--></style>
 <body>
    ''' % m)


#-------------------------------------------------------------------------------
#
def render_footer( oss ):
    """
    Render an HTML page footer.
    """
    oss.write('''
 </body>
</html>
    ''')

