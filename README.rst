|Build Status| |Coverage| |docs|

Salmon - A Python Mail Server
=============================

.. inclusion-marker-do-not-remove-start

Salmon is a pure Python mail server designed to create robust and complex mail
applications in the style of modern web frameworks. Salmon is designed to sit
behind a traditional mail server in the same way a web application sits behind
Apache or Nginx. It has all the features of a web application stack (templates,
routing, handlers, state machine) and plays well with other libraries, such as
Django and SQLAlchemy.

Salmon has been released uner the GNU GPLv3, as published by the FSF.

Features
========

Salmon supports running in many contexts for processing mail using the best
technology currently available. Since Salmon is aiming to be a modern mail
server and Mail processing framework, it has some features you don't find in
any other Mail server.

- Written in portable Python that should run on almost any Unix server.
- Handles mail in almost any encoding and format, including attachments, and
  canonicalizes them for easier processing.
- Sends nearly pristine clean mail that is easier to process by other
  receiving servers.
- Properly decodes internationalized mail into Python unicode, and translates
  Python unicode back into nice clean ascii and/or UTF-8 mail.
- Supports working with Maildir queues to defer work and distribute it to
  multiple machines.
- Can run as an non-root user on privileged ports to reduce the risk of
  intrusion.
- Salmon can also run in a completely separate virtualenv for easy deployment.
- A flexible and easy to use routing system lets you write stateful or state\
  *less* handlers of your email.
- Helpful tools for unit testing your email applications with nose, including
  spell checking with PyEnchant.
- Ability to use Jinja2 or Mako templates to craft emails including the
  headers.
- Easily configurable to use alternative sending and receiving systems,
  database libraries, or any other systems you need to talk to.
- Yet, you don't *have* to configure everything to get stated. A simple
  ``salmon gen`` command lets you get an application up and running quick.
- Finally, many helpful commands for general mail server debugging and
  cleaning.

Installing
==========

``pip install salmon-mail``

Project Information
===================

Project documentation can be found
`here <http://salmon-mail.readthedocs.org/>`__

Fork
----

Salmon is a fork of Lamson. In the summer of 2012 (2012-07-13 to be exact),
Lamson was relicensed under a BSD variant that was revokable.  The two clauses
that were of most concern::

    4. Contributors agree that any contributions are owned by the copyright holder
    and that contributors have absolutely no rights to their contributions.

    5. The copyright holder reserves the right to revoke this license on anyone who
    uses this copyrighted work at any time for any reason.

I read that to mean that I could make a contribution but then have said work
denied to me because the orginal author didn't like the colour of my socks. So
I went and found the latest version that was available under the GNU GPL
version 3.

Salmon is an anagram of Lamson, if you hadn't worked it out already.

Source
------

You can find the source on GitHub:

https://github.com/moggers87/salmon

Status
------

Salmon has just had some major changes to modernise the code-base. The main
APIs should be compatible with releases prior to 3.0.0, but there's no
guarantee that older applications won't need changes.

Python versions supported are: 2.7, 3.5, and 3.6.

See the CHANGELOG for more details on what's changed since version 2.

License
-------

Salmon is released under the GNU GPLv3 license, which can be found `here
<https://github.com/moggers87/salmon/blob/master/LICENSE>`__

Contributing
------------

Pull requests and issues are most welcome.

I will not accept code that has been submitted for inclusion in the original
project due to the terms of its new licence.

Testing
=======

The Salmon project needs unit tests, code reviews, coverage information, source
analysis, and security reviews to maintain quality. If you find a bug, please
take the time to write a test case that fails or provide a piece of mail that
causes the failure.

If you contribute new code then your code should have as much coverage as
possible, with a minimal amount of mocking.

Security
--------

Salmon follows the same security reporting model that has worked for other open
source projects: If you report a security vulnerability, it will be acted on
immediately and a fix with complete full disclosure will go out to everyone at
the same time. It's the job of the people using Salmon to keep track of
security relate problems.

Additionally, Salmon is written in as secure a manner as possible and assumes
that it is operating in a hostile environment. If you find Salmon doesn't
behave correctly given that constraint then please voice your concerns.

Development
===========

Salmon is written entirely in Python and runs on Python 2.7 with experimental
support for Python 3. It should hopefully run on any platform that supports
Python and has Unix semantics.

If you find yourself lost in source code, just yell.

PEP-8 should be followed where possible, but feel free to ignore the 80
character limit it imposes (120 is a good marker IMO).

.. inclusion-marker-do-not-remove-end

.. |Build Status| image:: https://travis-ci.org/moggers87/salmon.svg?branch=master
   :alt: Build Status
   :scale: 100%
   :target: https://travis-ci.org/moggers87/salmon
.. |Coverage| image:: https://codecov.io/github/moggers87/salmon/coverage.svg?branch=master
   :target: https://codecov.io/github/moggers87/salmon
   :alt: Coverage Status
   :scale: 100%
.. |docs| image:: https://readthedocs.org/projects/salmon-mail/badge/?version=latest
   :alt: Documentation Status
   :scale: 100%
   :target: https://salmon-mail.readthedocs.io/en/latest/?badge=latest
