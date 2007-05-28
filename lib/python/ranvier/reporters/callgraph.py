# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Call graph reporter.

This is an object that can be used for the code that reports the call graph.  To
be used only for debugging.
"""

# ranvier imports
from ranvier.reporters.reporter import SimpleReporter


__all__ = ('CallGraphReporter', 'FileCallGraphReporter')



class CallGraphReporter(SimpleReporter):
    """
    Interface for call graph reporters.
    See base class.
    """
    def end(self):
        if self.last_handled is None:
            return
        for target in self.rendered_list:
            self.publish_relation(self.last_handled, target)

    def publish_relation(self, caller, target):
        """
        Template method that you need to override to store/publish the
        relationship between two resources.
        """
        raise NotImplementedError



class FileCallGraphReporter(CallGraphReporter):
    """
    Concrete implementation that stores the mappings in a text file.  You can
    later process that with a script to produce a graphviz dot file. 
    """
    def __init__(self, outfile):
        CallGraphReporter.__init__(self)
        self.outf = outfile

    def publish_relation(self, caller, target):
        self.outf.write('%s %s\n' % (caller, target))

