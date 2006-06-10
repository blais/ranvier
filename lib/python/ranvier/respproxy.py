#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Response proxy: an base class for adapting to other web frameworks.

The response proxy is only used for us to be able to provide some resources that
are framework agnostic.  It provides an interface which you can derive from to
integrate those default resources into any framework.
"""

# stdlib imports
import sys, cgi


__all__ = ('ResponseProxy', 'CGIResponse')


#-------------------------------------------------------------------------------
#
class ResponseProxy(object):
    """
    Response proxy object.
    """
    def setContentType( self, contype ):
        """
        Sets the content type, perhaps even sends it to the client.
        """
        raise NotImplementedError

    def write( self, text ):
        """
        Write the given text to the output stream (to the client).
        """
        raise NotImplementedError

    def errorNotFound( self, msg=None ):
        """
        Signal an error to the client indicating that the resource was not
        found (404).
        """
        raise NotImplementedError

    def errorForbidden( self, msg=None ):
        """
        Signal an error to the client indicating that accessing the resource was
        forbidden.
        """
        raise NotImplementedError

    def redirect( self, target ):
        """
        Redirect the client's browser to another URL.
        """
        raise NotImplementedError

    def log( self, message ):
        """
        Send something to the log file.
        """
        raise NotImplementedError
        

#-------------------------------------------------------------------------------
#
class CGIResponse(ResponseProxy):
    """
    Simplistic response class for CGI programs.
    """
    def __init__( self, outfile=None ):
        ResponseProxy.__init__(self)

        self.contype = 'text/plain'
        """Content type, to be output upon first write."""

        self.headers = {}
        """Additional response headers."""

        self.wrote = False
        """Flag to indicate if we have written yet."""

        if outfile is None:
            outfile = sys.stdout
        self.outfile = outfile

    def setContentType( self, contype ):
        self.contype = contype

    def addHeader( self, header, content ):
        assert header not in self.headers
        self.headers[header] = content

    def write( self, text ):
        # Output the headers if we haven't yet done that.
        if self.wrote is False:
            # Output content-type
            self.outfile.write('Content-type: %s\n' % self.contype)

            # Output the headers
            for header, content in self.headers.iteritems():
                self.outfile.write('%s: %s\n' % (header, content))
            self.outfile.write('\n\n')
            self.wrote = True

        self.outfile.write(text)

    # These are very basic, you would most probably override them.

    def errorNotFound( self, msg=None ):
        if msg is None:
            msg = 'Document Not Found'
        self.addHeader('Status', '404 %s' % msg)
        self.setContentType('text/html')
        self.write('<html><body><p>%s</p></body></html>\n' % msg)
        return True

    def errorForbidden( self, msg=None ):
        if msg is None:
            msg = 'Access Denied'
        self.addHeader('Status', '403 %s' % msg)
        self.setContentType('text/html')
        self.write('<html><body><p>%s</p></body></html>\n' % msg)
        return True

    def redirect( self, target ):
        self.addHeader('Location', target)
        self.addHeader('Status', '302 Redirecting')
        self.write('Voila.\n')
        return True

    def log( self, message ):
        outf = sys.stderr
        outf.write(message)
        outf.flush()
        
#-------------------------------------------------------------------------------
#
def cgi_getargs():
    """
    Get the CGI arguments and convert them into a nice dictionary.
    This is a convenience method.
    """
    form = cgi.FieldStorage()

    args = {}
    for varname in form.keys():
        value = form[varname]

        if (isinstance(value, cgi.FieldStorage) and
            isinstance(value.file, file)):

            ovalue = value # FileUpload
        else:
            value = form.getlist(varname)
            if len(value) == 1:
                ovalue = value[0]
            else:
                ovalue = value

        args[varname] = ovalue

    return args

