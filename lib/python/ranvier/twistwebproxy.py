# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.
"""
Response proxy to work with Twisted.Web.

This is used to integrate code written for Ranvier within a standalone
Twisted.Web server.
"""

# stdlib imports
import sys, logging, re
from os.path import *
from StringIO import StringIO
from base64 import b64decode

# twisted imports
from twisted.web import server, resource, http, static
from zope.interface import implements

# ranvier imports
from ranvier.respproxy import ResponseProxy
from ranvier import RanvierBadRoot
from ranvier.context import HandlerContext



__all__ = ('DispatchResource',)


class TwistedWebResponseProxy(ResponseProxy):
    """
    Proxy for responding to Twisted.Web.
    """
    def __init__(self, twistreq):
        ResponseProxy.__init__(self)

        # A Twisted.Web Request object.
        self.twistreq = twistreq

        # A buffer to contain the response text.
        self.buffer = StringIO()
        
    def setContentType(self, contype):
        self.twistreq.setHeader("Content-type", contype)

    def addHeader(self, header, content):
        assert header.lower() not in self.twistreq.headers
        self.twistreq.setHeader(header, content)

    def value(self):
        return self.buffer.getvalue()

    def write(self, text):
        self.buffer.write(text)

    def errorNotFound(self, msg=None):
        self.addHeader('Status', '404 %s' % (msg or ''))
        self.twistreq.setHeader("Content-type", 'text/plain')
        self.twistreq.setResponseCode(http.NOT_FOUND)

    def errorForbidden(self, msg=None):
        self.addHeader('Status', '403 %s' % msg or '')
        self.twistreq.setResponseCode(http.FORBIDDEN)

    def redirect(self, target):
        self.twistreq.redirect(target)
        raise TwistedWebRedirect()

    def log(self, message):
        logging.info(message)


class TwistedWebRedirect(Exception):
    "An exception used to redirect control flow out of the handler on redirects."
    pass


class DispatchResource(object):
    """ A bogus Twisted resource that dispatche to our own slicker framework."""
    
    implements(resource.IResource)

    isLeaf = False

    def __init__(self, cfg, mapper, rootdir, ctxt_cls=HandlerContext):
        self.cfg = cfg
        self.mapper = mapper
        self.rootdir = rootdir
        self.ctxt_cls = ctxt_cls

    def getChildWithDefault(self, name, request):
        return self
    
    def putChild(self, path, child):
        raise NotImplementedError("This is not supported.")

    def render(self, request):

        if 'authorization' in request.received_headers:
            authstr = request.received_headers['authorization']
            mo = re.match('Basic (.*)$', authstr)
            assert mo, authstr
            username, password = b64decode(mo.group(1)).split(':')
        else:
            username = None
            
        # If the path is not at the root, we assume it's an error and just
        # redirect to the root automatically.
        path = request.path
        ##trace('path', path)

        # Handle the request with our response object.
        response = TwistedWebResponseProxy(request)

        badroot_redirect = 0
        try:
            ctxt = self.mapper.handle_request(
                request.method, path, request.args, response,
                ctxt_cls=self.ctxt_cls,
                cfg=self.cfg,
                referer=request.getHeader("referer") or None,
                auth_user=username)
        except TwistedWebRedirect:
            pass
        except RanvierBadRoot:
            badroot_redirect = 1
        
        # Serve files from a specific root directory.
        r = response.value()
        if badroot_redirect or request.code == http.NOT_FOUND:
            fn = join(self.rootdir, request.path[1:])
            if exists(fn) and isfile(fn):
                
                # Directly serve the file from our directory.
                request.setResponseCode(http.OK)
                f = static.File(fn)
                r = f.render(request)
                badroot_redirect = 0

        if badroot_redirect:
            request.setResponseCode(http.OK)
            request.redirect(self.mapper.rootloc + '/')
            r = ''
            
        return r


