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
      package_dir = {'': 'lib/python'},
      packages = ['ranvier', 'ranvier.reporters']
     )


