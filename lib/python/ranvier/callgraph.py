#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Call graph reporter.

This is an object that can be used for the code that reports the call graph.  To
be used only for debugging.
"""


class CallGraphReporter(object):
    """
    Interface for call graph reporters.
    """
    def __init__( self ):
        self.last_caller = None
        """The last caller resource-id."""

        self.target_list = []
        """The list of target resource-ids."""

    def register_caller( self, resid ):
        """
        Callback for caller resource-ids.
        """
        if resid is not None:
            self.last_caller = resid

    def register_target( self, resid ):
        """
        Callback for caller resource-ids.
        """
        self.target_list.append(resid)

    def complete( self ):
        """
        This method is called when resource handling for a request has been
        completed.
        """
        if self.last_caller is None:
            return
        for target in self.target_list:
            self.publish_relation(self.last_caller, target)

    def publish_relation( self, caller, target ):
        """
        Template method that you need to override to store/publish the
        relationship between two resources.
        """
        raise NotImplementedError


#-------------------------------------------------------------------------------
#
class FileCallGraphReporter(CallGraphReporter):
    """
    Concrete implementation that stores the mappings in a text file.  You can
    later process that with a script to produce a graphviz dot file. 
    """
    def __init__( self, outfile ):
        CallGraphReporter.__init__(self)
        self.outf = outfile

    def publish_relation( self, caller, target ):
        self.outf.write('%s %s\n' % (caller, target))
