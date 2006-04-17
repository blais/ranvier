#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Package import.  Just import this and you should be fine.
"""

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
# For debugging.
verbosity = 0

#-------------------------------------------------------------------------------
#
from resource import *
from context import *
from mapper import *
from folders import *
from miscres import *
from respproxy import *


