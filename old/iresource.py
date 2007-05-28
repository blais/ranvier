from interface import interface

class IResource(interface.Interface):
    """
    A web resource.

    This typically represent a component of a request.  The resource lookup is
    performed in a chain-of-responsibility pattern, each node having at its
    disposal the path and query arguments of the URL request.  Each node may
    modify this path according to the algorithm it implements.

    For example, the prototypical case is where we're implementing a tree
    structure similar to that of a directory structure.
    """

    def handle(ctxt, args):
        """
        Given a context object and the unparsed query arguments, handle the
        given request (or delegate it to someone else).  This is a very simple
        and flexible mechanism for handling the URL to resource mapping.
        """

class IHandlerContext(interface.Interface):
    """
    The context object contains

    - a path locator: a list of path components and a index of the
      current path component, which is meant to be updated during traversal.

    - the unparsed args: a copy of the args as given above (Note: we could
      and probably will eventually get rid of the explicitly passed args
      everywhere).

    Note that the context object can be used to pass around custom stuff
    from handler to handler.
    """

    locator = interface.Attribute("Locator.")
    args = interface.Attribute("Unparsed attributes.")


class IPathLocator(interface.Interface):
    """
    Interface to locator object used to resolve the paths.  It contain the URL
    path split by component.

    This object is meant to be updated as the traversal gets resolved, and has a
    notion of 'current' location.
    """
    def current(self):
        """
        Return the current component where parsing is occurring.
        """
        
    def getnext(self):
        """
        Return the next component where parsing is due to occur.
        """

    def next(self):
        """
        Move the current component to the next component (advance by one).
        """

    def isleaf(self):
        """
        Returns True if the current component is the leaf of the URL path.
        """

    def uri(self, idx=1000):
        """
        Return the joined URL path until the given idx.
        """

    def current_uri(self):
        """
        Return the full joined URL path.
        """

