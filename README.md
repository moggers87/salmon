The Salmon Mail Server

======================

Salmon is a pure Python SMTP server designed to create robust and complex mail
applications in the style of modern web frameworks such as Django. Unlike
traditional SMTP servers like Postfix or Sendmail, Salmon has all the features
of a web application stack (ORM, templates, routing, handlers, state machines,
Python) without needing to configure alias files, run newaliases, or juggle
tons of tiny fragile processes. Salmon also plays well with other web
frameworks and Python libraries.

Features
========

Salmon supports running in many contexts for processing mail using the best
technology currently available.  Since Salmon is aiming to be a modern SMTP
server and Mail processing framework, it has some features you don't find in any
other Mail server.

* Written in portable Python that should run on almost any Unix server.
* Handles mail in almost any encoding and format, including attachments, and
canonicalizes them for easier processing.
* Sends nearly pristine clean mail that is easier to process by other receiving
servers.
* Properly decodes internationalized mail into Python unicode, and translates
Python unicode back into nice clean ascii and/or UTF-8 mail.
* Salmon can use SQLAlchemy, TokyoCabinet, or any other database abstraction
layer or technology you can get libraries for.  It supports SQLAlchemy by
default.
* It uses Jinja2 by default, but you can swap in Mako if you like, or any other
template framework with a similar API.
* Supports working with Maildir queues to defer work and distribute it to
multiple machines.
* Can run as an non-root user on port 25 to reduce the risk of intrusion.
* Salmon can also run in a completely separate virtualenv for easy deployment.
* Spam filtering is baked into Salmon using the SpamBayes library.
* A flexible and easy to use routing system lets you write stateful or stateLESS
handlers of your email.
* Helpful tools for unit testing your email applications with nose, including
spell checking with PyEnchant.
* Ability to use Jinja2 or Mako templates to craft emails including the headers.
* A full alternative to the default optparse library for doing commands easily.
* Easily configurable to use alternative sending and receiving systems, database
libraries, or any other systems you need to talk to.
* Yet, you don't *have* to configure everything to get stated.  A simple
salmon gen command lets you get an application up and running quick.
* Finally, many helpful commands for general SMTP server debugging and cleaning.


Installing
==========

There's a setup.py

Project Information
===================

We, uh, don't really have any docs yet.

Fork
-----

Salmon is a fork of Lamson. In the summer of 2012 (2012-07-13 to be exact),
Lamson was relicenced under a BSD variant that was revokable. The two clauses
that were of most concern:

    4. Contributors agree that any contributions are owned by the copyright holder
    and that contributors have absolutely no rights to their contributions.

    5. The copyright holder reserves the right to revoke this license on anyone who
    uses this copyrighted work at any time for any reason.

I read that to mean that I could make a contribution but then have said work
denied to me because Mr. Shaw didn't like the colour of my socks. So I went and
found the latest version that was available under the GNU GPL version 3.

Salmon is an anagram of Lamson, if you hadn't worked it out already.

Source
-----

You can find the source on GitHub:

https://github.com/moggers87/salmon

Status
------

As this project has only just been forked, there may be bugs that have been
fixed upstream, but can't be backported due to licencing issues.  The source is
well documented, has nearly full test coverage, and runs on Python 2.6 and 2.7.


License
----

Salmon is released under the GNU GPLv3 license, which should be included with
your copy of the source code.  If you didn't receive a copy of the license then
you didn't get the right version of the source code.


Contributing
-------

Pull requests and issues are most welcome.

I will not accept code that has been submitted for inclusion in the original
project, due to the terms of its licence. Unless you have permission from Zed
Shaw.

Testing
=======

The Salmon project needs unit tests, code reviews, coverage information, source
analysis, and security reviews to maintain quality.  If you find a bug, please
take the time to write a test case that fails or provide a piece of mail that
causes the failure.

If you contribute new code then your code should have as much coverage as
possible, with a minimal amount of mocking.


Security
--------

Salmon follows the same security reporting model that has worked for other open
source projects:  If you report a security vulnerability, it will be acted on
immediately and a fix with complete full disclosure will go out to everyone at
the same time.  It's the job of the people using Salmon to keep track of
security relate problems.

Additionally, Salmon is written in as secure a manner as possible and assumes
that it is operating in a hostile environment.  If you find Salmon doesn't
behave correctly given that constraint then please voice your concerns.



Development
===========

Salmon is written entirely in Python and runs on Python 2.6 or 2.7 but not 3k
yet.  It uses only pure Python except where some libraries have compiled
extensions (such as Jinja2).  It should hopefully run on any platform that
supports Python and has Unix semantics.

The code is consistently documented and written to be read in an instructional
manner where possible.  If a piece of code does not make sense, then ask for
help and it will be clarified.  The code is also small and has a full test suite
with about 95% coverage, so you should be able to find out just about anything
you need to hack on Salmon in the Salmon source.

Given the above statements, it should be possible for anyone to take the Salmon
source and read through it in an evening or two.  You should also be able to
understand what's going on, and learn anything you don't by asking questions.

If this isn't the case, then feel free to ask for help understanding it.


