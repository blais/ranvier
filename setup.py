#!/usr/bin/env python

"""
Install script for the Ranvier URM Mapper project.
"""

__author__ = "Martin Blais <blais@furius.ca>"

import sys
from distutils.core import setup

def read_version():
    try:
        return open('VERSION', 'r').readline().strip()
    except IOError, e:
        raise SystemExit(
            "Error: you must run setup from the root directory (%s)" % str(e))


# Include all files without having to create MANIFEST.in
def add_all_files(fun):
    import os, os.path
    from os.path import abspath, dirname, join
    def f(self):
        for root, dirs, files in os.walk('.'):
            if '.hg' in dirs: dirs.remove('.hg')
            self.filelist.extend(join(root[2:], fn) for fn in files
                                 if not fn.endswith('.pyc'))
        return fun(self)
    return f
from distutils.command.sdist import sdist
sdist.add_defaults = add_all_files(sdist.add_defaults)


setup(name="ranvier",
      version=read_version(),
      description=\
      "A Powerful URL Mapping Python Library",
      long_description="""
Ranvier is a Python library that can be integrated in any web application
framework to map an incoming URL to a resource (controller).

It can also serve as a central registry of all the URLs that are served from a
web application and can generate the URLs necessary for cross-linking pages.  If
you use this library to map and generate all your URLs you should be able to
completely rearrange the layout of your site without breaking the pages nor the
tests.
""",
      license="GPL",
      author="Martin Blais",
      author_email="blais@furius.ca",
      url="http://furius.ca/ranvier",
      download_url="http://bitbucket.org/blais/ranvier",
      package_dir = {'': 'lib/python'},
      packages = ['ranvier', 'ranvier.reporters']
     )
