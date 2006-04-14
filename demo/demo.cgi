#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Ranvier demo application.

This demonstrates the URL mapping capabilities of Ranvier.

Note: This simple web application is built with a simple CGI script and an
apache redirect rule to provide clean URLs for the mapping demo.  We do it like
this because this reduces long-term maintenance issues: CGI is not about to go
away and it is easy to configure on my server.  Further, it really shows that
the Ranvier package is framework-agnostic and that you can integrate it within
any web application framework out there.
"""

# stdlib imports
import sys, os, urlparse
from os.path import dirname, join
import cgi, cgitb; cgitb.enable()
import cPickle as pickle

# Add the Ranvier libraries to the load-path to minimize configuration (this is
# *only* a CGI script after all).
root = dirname(dirname(sys.argv[0]))
sys.path.append(join(root, 'lib', 'python'))

# ranvier imports
from ranvier import *


#-------------------------------------------------------------------------------
#
remroot = '/ranvier/demo'

def main():
    """
    CGI handler for debugging/dumping the contents of the source upload.
    """
    uri = os.environ['SCRIPT_URI']
    scheme, netloc, path, parameters, query, fragid = urlparse.urlparse(uri)
    
    assert path.startswith(remroot)
    path = path[len(remroot):]

    # Create a context for resource handling.
    form = cgi.FieldStorage()
    ctxt = HandlerContext(path, form, root=remroot)
    ctxt.response = CGIResponse(sys.stdout)

    # Create the application.
    #
    # Note: this is a bit silly, we recreate the entire resource tree on every
    # request.  In a "real" web application, your process is a running for a
    # long time and this happens only once for every child.
    root = create_application()

    # Handle the resource.
    return root.handle(ctxt)

#-------------------------------------------------------------------------------
#
def render_header( ctxt ):
    header = """
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<link rel="stylesheet" href="/ranvier/demo/style.css" type="text/css" />
</head>
<body>

<div id="project-header">
  <a href="/ranvier/demo/">
  <img src="/home/furius-logo-w.png" id="logo"></a>
</div>

<div id="blurb-container">
<div id="blurb">
<p>
You are currently viewing a demo application for the URL mapping capabilities of
<a href="/ranvier">Ranvier</a>.
</p>
</div>
</div>

<div id="main" class="document">

"""
    ctxt.response.setContentType('text/html')
    ctxt.response.write(header)

    
def render_footer( ctxt ):
    ctxt.response.write("""

</div>
</body></html>
""")
    

#-------------------------------------------------------------------------------
#
class DemoFolderWithMenu(FolderWithMenu):
    """
    Our prettified folder class.
    """
    def default_menu( self, ctxt ):
        render_header(ctxt)
        menu = self.genmenu(ctxt)
        ctxt.response.write(menu)
        render_footer(ctxt)
        

#-------------------------------------------------------------------------------
#
def create_application():
    """
    Create a tree of application resources and return the corresponding root
    resource.
    """

    root = DemoFolderWithMenu('home', home=Home())

    return root



#-------------------------------------------------------------------------------
#
class Home(Resource):
    def handle( self, ctxt ):
        render_header(ctxt)

        ctxt.response.write("""
<h1>Demo Home</h1>





""")
        render_footer(ctxt)

#-------------------------------------------------------------------------------
#
if __name__ == '__main__':
    main()

