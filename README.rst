====================================
   ranvier: A Powerful URL Mapper
====================================

.. contents:: Table of Contents


Description
===========

Ranvier is a Python package that can be integrated in web application
frameworks to map incoming URL requests to source code.  It also
serves as a central registry of all the URLs in a web application and
can itself generate the URLs necessary for cross-linking pages.  This
mechanism allows web application writers let go of writing URLs
manually and provides a powerful mechanism to check for incorrect
links at render time.  In addition, a live application can provide the
list of resources that it serves at runtime, both for developer
documentation or computer consumption.  This allows test components
for resources to be easily reused across application instances and to
perform static checking of links in the source (without running any
application code) and provides for testing coverage of accessed and
rendered links.  If you use this library to generate all your URLs you
should be able to easily rearrange the entire layout of your site
without breaking any links.  Ranvier is pure Python code and does not
have any 3rd-party dependencies;  it should be usable in any
Python-based web application framework.


Dependencies
============

- Python 2.4 or more


Documentation
=============

* `Documentation <doc/ranvier-doc.html>`_
* `Differences with Routes <doc/differences-with-routes.html>`_


Demo
----

There is a `running demo of this code HERE`__.

__ /ranvier/demo


Download
========

A Mercurial repository can be found at:

  http://github.com/blais/ranvier


Links
=====

- This is similar in spirit to the Routes__ system implemented in Ruby-on-Rails
  and by its namesake Python library.

__ ???


Copyright and License
=====================

Copyright (C) 2005-2006  Martin Blais.
This code is distributed under the `GNU General Public License <COPYING>`_.


Author
======

Martin Blais <blais@furius.ca>
