# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Read-only dictionary.
"""


__all__ = ()



class ReadOnlyDict(object):
    """
    A base class that is meant to provide read-only dictionary interface to an
    object which has access to the dictionary contents.
    """
    def __init__(self, *params, **kwds):
        self.rwdict = dict(*params, **kwds)

    def __contains__(self, resid):
        return self.rwdict.__contains__(resid)

    def __getitem__(self, resid):
        return self.rwdict.__getitem__(resid)

    def has_key(self, resid):
        return self.rwdict.has_key(resid)

    def items(self):
        return self.rwdict.items()

    def iteritems(self):
        return self.rwdict.iteritems()

    def keys(self):
        return self.rwdict.keys()

    def iterkeys(self):
        return self.rwdict.iterkeys()

    def values(self):
        return self.rwdict.values()

    def itervalues(self):
        return self.rwdict.itervalues()


