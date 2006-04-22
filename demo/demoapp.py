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
def create_application( rootloc=None ):
    """
    Create a tree of application resources and return the corresponding root
    resource.  'rootlocation' is the root directory to which the resource tree
    is bound on the site.
    """
    mapper = UrlMapper(rootloc=rootloc)
    root = Folder(
        _default='home',
        home=Home(),
        altit=SpecialResource(resid='@@ImSpecial'),
        resources=EnumResource(mapper),
        prettyres=DemoPrettyEnumResource(mapper, True),
        deleg=Augmenter(AnswerBabbler()),
        users=UsernameRoot(Folder(username=PrintUsername(),
                                  name=PrintName(),
                                  data=UserData())),
        redirtest=RedirectResource('@@Home', resid='@@RedirectTest'),
        internalredir=InternalRedirectTest(),
        lcomp=LeafPlusOneComponent(),

        fold=DemoFolderWithMenu(
           greed=SimpleResource("Nature has given enough to meet man's need "
                                "but not enough to meet man's greed.",
                                resid="@@SimpleGreed"),
           think=SimpleResource("There are wavelengths that people cannot see, "
                                "there are sounds that people cannot hear, and "
                                "maybe computers have thoughts that people "
                                "cannot think.", resid="@@SimpleThought"),
           ham=SimpleResource("The purpose of computing is insight, not "
                              "numbers.", resid="@@SimpleHamming"),
           ),
        resid='@@Root'
        )

    mapper.initialize(root)
    mapper.add_static('@@ExternalExample', 'http://paulgraham.com')

    return mapper, root


#-------------------------------------------------------------------------------
#
class PageLayout:
    """
    A class that provides common rendering routines for a page's layout.
    """
    def __init__( self, mapper ):
        self.mapper = mapper
    
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
 """ % {'root': self.mapper.mapurl('@@Root')}

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
    def handle_default( self, ctxt ):
        ctxt.page.render_header(ctxt)
        menu = self.genmenu(ctxt)
        ctxt.response.write(menu)
        ctxt.page.render_footer(ctxt)


class SimpleResource(LeafResource):
    """
    A simplistic resource that just outputs a message.
    """
    def __init__( self, msg, **kwds ) :
        LeafResource.__init__(self, **kwds)
        self.msg = msg

    def handle( self, ctxt ):
        ctxt.page.render_header(ctxt)
        ctxt.response.write(self.msg)
        ctxt.page.render_footer(ctxt)


#-------------------------------------------------------------------------------
#
class InternalRedirectTest(LeafResource):
    """
    A simple internal redirect, with parameters.
    """
    def handle( self, ctxt ):
        ctxt.redirect(ctxt.mapurl('@@PrintUsername', username='martin'))

#-------------------------------------------------------------------------------
#
class DemoPrettyEnumResource(PrettyEnumResource):
    """
    A renderer for pretty resources within our template.
    """
    def handle( self, ctxt ):
        ctxt.page.render_header(ctxt)
        ctxt.response.write(pretty_render_mapper_body(self.mapper,
                                                      dict(ctxt.args),
                                                      self.sorturls))
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
        mapurl = ctxt.mapurl

        # Creating links to be replaced in the template.  You would have some
        # kind of system specific to your template language here.
        m = {'home': mapurl('@@Home'),
             'pretty': mapurl('@@DemoPrettyEnumResource'),
             'plain': mapurl('@@EnumResource'),
             'altid': mapurl('@@ImSpecial'),
             'answer': mapurl('@@AnswerBabbler'),
             'username': mapurl('@@PrintUsername', username='martin'),
             'name': mapurl('@@PrintName', 'martin'),
             'extredir': mapurl('@@RedirectTest'),
             'intredir': mapurl('@@InternalRedirectTest'),
             'leafcomp': mapurl('@@LeafPlusOneComponent', comp='president'),
             'folddemo': mapurl('@@DemoFolderWithMenu'),
             'static': mapurl('@@ExternalExample'),
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

  <li> <b>Home Page</b>: You are at the <a href="%(home)s" target="testwin">home
  page</a> </li>

  <li> <b>Pretty Print</b>: While the page you\'re currently viewing has been
  crafted byhand, you can also find an <a href="%(pretty)s"
  target="testwin">automatically-generated pretty rendering</a> of the resources
  available in this demo </li>

  <li> <b>Plain Sitemap</b>: In the same spirit of generating site maps
  automatically, we can also generate <a href="%(plain)s" target="testwin">plain
  text sitemaps</a> that can be served for programs to parse and rebuild a
  mapper from them.  </li>

  <li> <b>Alternate Id</b>:  Some resources can be given user-provided resource
  ids, for example, <a href="%(altid)s" target="testwin">this link</a> was
  accessed with the id "ImSpecial".  This is required when you have multiple
  instances of the same resource class, to back, you need to disambiguate which
  instance is concerned.  </li>

  <li> <b>Consumer</b>: In the forward mapping carried out by the chain of
  responsibility, you can consume part of the URL.  This is useful for building
  a set of resources referring to the same object.  Check out the follow user\'s
  <a href="%(username)s" target="testwin">username</a> and <a href="%(name)s"
  target="testwin">name</a>.  </li>

  <li> <b>Delegater</b>: The chain of responsibility pattern does not imply that
  each resource consume a part of the component.  We have a base class that
  makes that process a little bit easier.  Check this one: it provides <a
  href="%(answer)s" target="testwin">the answer to everything</a>! </li>

  <li> <b>Redirect</b>: A test for <a href="%(extredir)s"
  target="testwin">external redirection</a>, that should just redirect here, and
  one for <a href="%(intredir)s" target="testwin">internal redirection</a> that
  should redirect somewhere else (technically, the location of your
  client/browser should not change for this one). </li>

  <li> <b>Leaf Component</b>: Simple test case for a <a href="%(leafcomp)s"
  target="testwin">component located at the leaf</a>. </li>

  <li> <b>Folder With Menu</b>: We provide a <a href="%(folddemo)s"
  target="testwin"> folder resource class</a> that allows you to build
  hierarchies of resources, like a directory and files.  This one automatically
  provides a menu of its subresources.</li>

  <li> <b>Static Mappings</b>: You can register static/external mappings with
  the URL mapper.  For example, <a href="%(static)s" target="testwin">this
  link</a> should point somewhere interesting on the web. </li>

</ul>
        ''' % m)

        ctxt.page.render_footer(ctxt)


#-------------------------------------------------------------------------------
#
class UsernameRoot(VarDelegaterResource):
    """
    This is an example of consuming part of the locator.  Part of the this
    resource is a username.  It just accepts any username that is all lowercase
    letters, and indicates not found for any other.  It could do this with a
    database, in a real application.
    """
    def __init__( self, next, **kwds ):
        VarDelegaterResource.__init__(self, 'username', next, **kwds)

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


class UserData(VarResource):
    """
    Select some user data.  We do this only to show off getting multiple
    components in the same path.
    """
    def __init__( self, **kwds ):
        VarResource.__init__(self, 'userdata', **kwds)

    def handle( self, ctxt ):
        ctxt.page.render_header(ctxt)
        ctxt.response.write(
            '''<p>The data for user "%(username)s" is "%(data)s".</p>''' %
            {'username': ctxt.username, 'data': ctxt.userdata})
        ctxt.page.render_footer(ctxt)


#-------------------------------------------------------------------------------
#
class LeafPlusOneComponent(VarResource):
    """
    Example resource that consumes the leaf of the locator path, i.e. it is not
    a leaf, but the component itself is the leaf.
    """
    def __init__( self, **kwds ):
        VarResource.__init__(self, 'comp')

    def handle( self, ctxt ):
        # Render a page with the last component.
        ctxt.page.render_header(ctxt)
        ctxt.response.write('''<p>The leaf component is %s.</p>''' %
                            ctxt.comp)
        ctxt.page.render_footer(ctxt)



