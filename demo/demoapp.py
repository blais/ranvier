#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Resources setup for the Ranvier demo.
"""


# ranvier imports
from ranvier import *


#-------------------------------------------------------------------------------
#
def create_application( rootloc ):
    """
    Create a tree of application resources and return the corresponding root
    resource.  'rootlocation' is the root directory to which the resource tree
    is bound on the site.
    """
    mapper = UrlMapper(rootloc=rootloc)
    root = DemoFolderWithMenu('home',
                              home=Home(mapper),
                              resources=EnumResource(mapper),
                              prettyres=PrettyEnumResource(mapper))

    mapper.initialize(root)
    return mapper, root


#-------------------------------------------------------------------------------
#
class DemoFolderWithMenu(FolderWithMenu):
    """
    Our prettified folder class.
    """
    def default_menu( self, ctxt ):
        ctxt.page.render_header(ctxt)

        menu = self.genmenu(ctxt)
        ctxt.response.write(menu)

        ctxt.page.render_footer(ctxt)

#-------------------------------------------------------------------------------
#
class Home(Resource):
    def __init__( self, mapper ):
        self.mapper = mapper
        
    def handle( self, ctxt ):
        ctxt.page.render_header(ctxt)

        ctxt.response.write("""
<h1>Demo Home</h1>
<p>
This is the root of the Ranvier demo program.  This tree is served by using the
mapper and the links contained are also rendered using the mapper.
</p>

<p>
Here are the resources available here:
</p>
<ul>
""")
        for o in self.mapper.getmappings():
            print '<li><a href="%s">%s</a> (%s)</li>' % (o.url, o.resid, o.url)
        
        ctxt.response.write("""
</ul>
""")

        ctxt.page.render_footer(ctxt)


#-------------------------------------------------------------------------------
#
class DemoPrettyEnumResource(PrettyEnumResource):
    """
    A renderer for pretty resources within our template.
    """
    def handle( self, ctxt ):
        ctxt.page.render_header(ctxt)
        ctxt.response.write(self.mapper.pretty_render())
        ctxt.page.render_footer(ctxt)


