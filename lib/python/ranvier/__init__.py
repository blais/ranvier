#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Package import.  Just import this and you should be fine.
"""


#-------------------------------------------------------------------------------
#
# Global flag used to turn on some debugging and tracing for development.
_verbosity = 0


#-------------------------------------------------------------------------------
#
class RanvierError(Exception):
    """
    Class used for errors due to the misuse of the Atocha API.  An occurrence of
    this exception means that you most likely have made a mistake in your code
    using Atocha.
    """

#-------------------------------------------------------------------------------
#
def _atat_namexform(clsname):
    """
    Use the class' name, prepended with two @ signs.  This kind of string rarely
    occurs in Python code and makes it easy to grep for all of them later on in
    the codebase/templates.  Some of the support tools also assume this function
    by default.
    """
    return '@@' + clsname

# The global function to transform resource instances/classes into names.
_namexform = _atat_namexform

def set_resource_id_name_function(fun):
    """
    Set the global function that is used to automatically compute the
    resource-id of a resource object if it has not been given an explicit one.

    The given function should be a callable that is used to calculate an
    appropriate resource-id from the resource instance.  You can override this
    to provide your own favourite scheme.
    """
    global _namexform
    _namexform = fun




#-------------------------------------------------------------------------------
#
from resource import *
from context import *
from mapper import *
from folders import *
from miscres import *
from respproxy import *
from pretty import *
from reporters.reporter import *
from reporters.callgraph import *
from reporters.coverage import *
from reporters.tracer import *


# Remove stuff that we don't want to export in a star-export.
from types import ModuleType as _modtype
__all__ = tuple(k for k, v in globals().iteritems()
                if not k.startswith('_') and not isinstance(v, _modtype))

