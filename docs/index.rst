.. Salmon documentation master file, created by
   sphinx-quickstart on Mon Aug 24 22:13:47 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. A lot of this material should be in README.md too

Salmon - A Python Mail Server
=============================

Salmon is a pure Python mail server designed to create robust and complex mail
applications in the style of modern web frameworks. Unlike traditional mail
servers such as Postfix and Sendmail, Salmon has all the features of a web
application stack (templates, routing, handlers, state machine, Python) without
the need to configure alias files, arcane command syntax, or juggle a swarm of
fragile processes. Salmon also plays well with other frameworks and libraries,
such as Django and SQLAlchemy.

Salmon has been released under the GNU GPLv3, as published by the FSF.


Contents:

.. toctree::
    :maxdepth: 2

    getting_started
    routing
    relaying
    mail_objects
    Salmon API guide <salmon>

About Salmon
============

.. toctree::
    :maxdepth: 2

    changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

