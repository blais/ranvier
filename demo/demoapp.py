#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Resources setup for the Ranvier demo.
"""

# stdlib imports
import re

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
    root = DemoFolderWithMenu(
        'home',
        home=Home(),
        altit=SpecialResource(resid='@@ImSpecial'),
        resources=EnumResource(mapper),
        prettyres=DemoPrettyEnumResource(mapper),
        deleg=Augmenter(AnswerBabbler()),
        users=UsernameRoot(Folder(username=PrintUsername(),
                                  name=PrintName())),
        redirtest=Redirect('@@Home', resid='@@RedirectTest'),
        )

    mapper.initialize(root)
    return mapper, root


#-------------------------------------------------------------------------------
#
class PageLayout:
    """
    A class that provides common rendering routines for a page's layout.
    """
    def __init__( self, rootloc ):
        self.rootloc = rootloc
    
    def render_header( self, ctxt ):
        header = """
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <link rel="stylesheet" href="%(root)s/style.css" type="text/css" />
  </head>
  <body>

    <div id="project-header">
      <a href="%(root)s/">
      <img src="/home/furius-logo-w.png" id="logo"></a>
    </div>
    
    <div id="blurb-container">
    <div id="blurb">
    <p>
    You are currently viewing a <a href="%(root)s">demo application</a> for the
    URL mapping capabilities of <a href="/ranvier">Ranvier</a>.
    </p>
    </div>
    </div>
    
    <div id="main" class="document">
 """ % {'root': self.rootloc}

        ctxt.response.setContentType('text/html')
        ctxt.response.write(header)

    def render_footer( self, ctxt ):
        ctxt.response.write("""
    </div>
  </body>
</html>
""")

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
class DemoPrettyEnumResource(PrettyEnumResource):
    """
    A renderer for pretty resources within our template.
    """
    def handle( self, ctxt ):
        ctxt.page.render_header(ctxt)
        ctxt.response.write(pretty_render_mapper_body(self.mapper))
        ctxt.page.render_footer(ctxt)


#-------------------------------------------------------------------------------
#
class SpecialResource(LeafResource):
    """
    A resource referred to using an alternate id.
    """
    def handle( self, ctxt ):
        ctxt.page.render_header(ctxt)
        ctxt.response.write("""
        <p>Well, I'm not that special, really.</p>""")
        ctxt.page.render_footer(ctxt)
        
#-------------------------------------------------------------------------------
#
class Augmenter(DelegaterResource):
    """
    A resource that adds the answer to Life, the Universe and Everything to the
    context.
    """
    def handle( self, ctxt ):
        ctxt.answer = 42

class AnswerBabbler(LeafResource):
    """
    We just print the answer.
    """
    def handle( self, ctxt ):
        ctxt.page.render_header(ctxt)
        ctxt.response.write("""
        <p>
        The answer is: %d
        </p>""" % ctxt.answer)
        ctxt.page.render_footer(ctxt)

#-------------------------------------------------------------------------------
#
class Home(LeafResource):
    """
    Root page of the demo.
    """
    def handle( self, ctxt ):
        ctxt.page.render_header(ctxt)

        # This could be done globally
        url = ctxt.mapper.url

        # Creating links to be replaced in the template.  You would have some
        # kind of system specific to your template language here.
        m = {'home': url('@@Home'),
             'pretty': url('@@DemoPrettyEnumResource'),
             'plain': url('@@EnumResource'),
             'altid': url('@@ImSpecial'),
             'answer': url('@@AnswerBabbler'),
             'username': url('@@PrintUsername', username='martin'),
             'name': url('@@PrintName', username='martin'),
             'red': url('@@RedirectTest'),
             }

        ctxt.response.write('''
<h1>Demo Home</h1>

<p>
This is the root of the Ranvier demo program.  This tree is served by using the
mapper and the links contained are also rendered using the mapper.  This is
actually not very exciting unless you have a look at the source code.
</p>

<p>
Here are the resources available here:
</p>
<ul>

  <li> <b>Home Page</b>: You are at the <a href="%(home)s">home page</a> </li>

  <li> <b>Pretty Print</b>: While the page you\'re currently viewing has been
  crafted byhand, you can also find an <a
  href="%(pretty)s">automatically-generated pretty rendering</a> of the
  resources available in this demo </li>

  <li> <b>Plain Sitemap</b>: In the same spirit of generating site maps
  automatically, we can also generate <a href="%(plain)s">plain text
  sitemaps</a> that can be served for programs to parse and rebuild a mapper
  from them.  </li>

  <li> <b>Alternate Id</b>:  Some resources can be given user-provided resource
  ids, for example, <a href="%(altid)s">this link</a> was accessed with the id
  "ImSpecial".  This is required when you have multiple instances of the same
  resource class, to back, you need to disambiguate which instance is concerned.
  </li>

  <li> <b>Consumer</b>: In the forward mapping carried out by the chain of
  responsibility, you can consume part of the URL.  This is useful for building
  a set of resources referring to the same object.  Check out the follow user\'s
  <a href="%(username)s">username</a> and <a href="%(name)s">name</a>.  </li>

  <li> <b>Delegater</b>: The chain of responsibility pattern does not imply that
  each resource consume a part of the component.  We have a base class that
  makes that process a little bit easier.  Check this one: it provides
  <a href="%(answer)s">the answer to everything</a>! </li>

  <li> <b>Redirect</b>: A test for redirection, that should just <a
  href="%(red)s">redirect here</a>. </li>

</ul>
        ''' % m)

        ctxt.page.render_footer(ctxt)


#-------------------------------------------------------------------------------
#
class UsernameRoot(CompVarResource):
    """
    This is an example of consuming part of the locator.  Part of the this
    resource is a username.  It just accepts any username that is all lowercase
    letters, and indicates not found for any other.  It could do this with a
    database, in a real application.
    """
    def __init__( self, next, **kwds ):
        CompVarResource.__init__(self, 'username', next, **kwds)

    def handle( self, ctxt ):
        if not re.match('[a-z]+$', ctxt.username):
            return ctxt.response.errorNotFound()

        ctxt.name = 'Mr or Mrs %s' % ctxt.username.capitalize()


class PrintUsername(LeafResource):
    """
    This resource prints a username that has been consumed along the URL path
    that maps into this resource..
    """
    def handle( self, ctxt ):
        ctxt.page.render_header(ctxt)
        ctxt.response.write('''<p>The username is %(username)s.</p>''' %
                            {'username': ctxt.username})
        ctxt.page.render_footer(ctxt)

class PrintName(LeafResource):
    """
    This resource prints a username that has been consumed along the URL path
    that maps into this resource..
    """
    def handle( self, ctxt ):
        ctxt.page.render_header(ctxt)
        ctxt.response.write('''<p>The user\'s name is %(name)s.</p>''' %
                            {'name': ctxt.name})
        ctxt.page.render_footer(ctxt)

