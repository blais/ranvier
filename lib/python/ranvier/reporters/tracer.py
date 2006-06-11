#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Tracer reporter.

A reporter that accumulates the resource ids that have been placed on the path
and that at the end of the request outputs what to some tracing function.
"""

# ranvier imports
from ranvier.reporters.reporter import ResourceReporter


__all__ = ('TracerReporter',)


#-------------------------------------------------------------------------------
#
class TracerReporter(ResourceReporter):
    """
    A reporter that accumulates the resource ids that have been placed on the
    path and that at the end of the request outputs what to some tracing
    function.
    """
    def __init__(self, outfunc):

        assert outfunc
        self.outfunc = outfunc
        """'A function to log the resource-id path."""
        
    def begin(self):
        self.accu = []

    def register_handled(self, resid):
        self.accu.append(resid)

    def register_rendered(self, resid):
        pass

    def end(self):
        self.outfunc(' -> '.join(self.accu))

