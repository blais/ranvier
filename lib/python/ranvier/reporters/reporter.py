#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Base class for all reporters.

Reporters are called upon when a resource is being handled (delegated) and when
a URL is being mapped back for a resource.  The callgraph generator and the
coverage analysis tool both use it.
"""


__all__ = ('ResourceReporter', 'SimpleReporter')


class ResourceReporter(object):
    """
    Interface for all reporters.
    """
    def register_handled(self, resid):
        """
        Callback for caller resource-ids.
        """
        raise NotImplementedError

    def register_rendered(self, resid):
        """
        Callback for caller resource-ids.
        """
        raise NotImplementedError

    def begin(self):
        """
        Initialize the reporter for handling a request.
        """
        # Noop.

    def end(self):
        """
        This method is called when resource handling for a request has been
        completed.
        """
        # Noop.


class SimpleReporter(ResourceReporter):
    """
    Base class for all reporters that do not need to access the intermediate
    resources that are being handled (only the final leaf resource that handles
    the request is kept).
    """
    def __init__(self):
        self.last_handled = None
        """The last caller resource-id."""

        self.rendered_list = []
        """The list of target resource-ids."""

    def register_handled(self, resid):
        """
        Callback for caller resource-ids.
        """
        if resid is not None:
            self.last_handled = resid

    def register_rendered(self, resid):
        """
        Callback for caller resource-ids.
        """
        self.rendered_list.append(resid)

    def begin(self):
        self.last_handled = None
        self.rendered_list = []

