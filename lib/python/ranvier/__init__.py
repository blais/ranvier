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
from resource import *
from context import *
from mapper import *
from folders import *
from miscres import *
from respproxy import *
from pretty import *
from callgraph import *


# Remove stuff that we don't want to export in a star-export.
from types import ModuleType as _modtype
__all__ = tuple(k for k, v in globals().iteritems()
                if not k.startswith('_') and not isinstance(v, _modtype))

