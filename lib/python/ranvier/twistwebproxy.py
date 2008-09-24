# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.
"""
Response proxy to work with Twisted.Web.

This is used to integrate code written for Ranvier within a standalone
Twisted.Web server.
"""

# stdlib imports
from os.path import *
from StringIO import StringIO

# twisted imports
from twisted.web import server, resource, http, static
from zope.interface import implements

# ranvier imports
from ranvier.respproxy import ResponseProxy
from ranvier.context import HandlerContext



__all__ = ('TwistedWebResponseProxy', 'DispatchResource')


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
        self.addHeader('Status', '404 %s' % msg or '')
        self.twistreq.setResponseCode(http.NOT_FOUND)

    def errorForbidden(self, msg=None):
        self.addHeader('Status', '403 %s' % msg or '')
        self.twistreq.setResponseCode(http.FORBIDDEN)

    def redirect(self, target):
        self.twistreq.redirect(url)

    def log(self, message):
        logging.info(message)



class DispatchResource(object):
    """ A bogus Twisted resource that dispatche to our own slicker framework."""
    
    implements(resource.IResource)

    isLeaf = False

    def __init__(self, cfg, mapper, rootdir):
        self.cfg = cfg
        self.mapper = mapper
        self.rootdir = rootdir

    def getChildWithDefault(self, name, request):
        return self
    
    def putChild(self, path, child):
        raise NotImplementedError("This is not supported.")

    def render(self, request):

        # Handle the request with our response object.
        response = TwistedWebResponseProxy(request)
        ctxt = self.mapper.handle_request(
            request.method, request.path, request.args, response,
            ctxt_cls=HandlerContext, cfg=self.cfg)

        # Serve files from a specific root directory.
        r = response.value()
        if request.code == http.NOT_FOUND:
            fn = join(self.rootdir, request.path[1:])
            if exists(fn):

                # Directly serve the file from our directory.
                request.setResponseCode(http.OK)
                f = static.File(fn)
                r = f.render(request)
            
        return r


