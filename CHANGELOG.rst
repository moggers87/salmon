.. _three-two-zero-rc1:

3.2.0rc1
========

:release-date: 2019-12-06

- Switch from argparse to click (#80)

   - Commandline interface is now documented
   - Salmon now exits with non-zero return codes (#112)

- ``salmon.server.QueueReceiver`` now uses threads (#67)

   - For those using ``@nolocking``, this will mean massive improvements in performance

- ``salmon.queue.Queue`` now implements ``__len__``
- Remove nosetests and just use Python's builtin unit test modules (#96)
- Directories required for Salmon startup will now be created if they don't exist (#111)
- Fix routes, blast, and cleanse commands (#102, #103)
- Python 3.8 is now supported

.. _three-one-one:

3.1.1
=====

:release-date: 2019-05-28

- Require newer versions of python-daemon to properly fix the install issues we
  had previously (#89)
- Fixed a bug in ``salmon.queue.Queue`` that mangled mail if it was added as
  ``bytes`` rather than a message-like object (#97)

.. _three-one-zero:

3.1.0
=====

:release-date: 2019-01-17

- Support for Python 3.7
- Don't install python-daemon 2.2.0, it breaks things (#89)
- Remove untested spelling function (#86)

  - The spelling function did very little other than assume it could load
    PyEnchant and then ``return True`` if it couldn't. If you really miss this
    function, submit a PR with something that actually works and has tests!

.. _three-zero-two:

3.0.2
=====

:release-date: 2018-07-21

- Fixed a bug where the version string would be a bytes literal under Python 3 (#83)

.. _three-zero-one:

3.0.1
=====

:release-date: 2018-06-12

- ``SMTPReceiver.process_messsage`` now accepts keyword arguments added in
  Python 3

.. _three-zero-zero:

3.0.0
=====

:release-date: 2017-12-31

- No changes since :ref:`three-zero-zero-rc1`

.. _three-zero-zero-rc1:

3.0.0rc1
========

:release-date: 2017-12-31

- Removed lots of cruft (#19)
- Moved from modargs to argparse - command line interface has changed (#28)

  - Improved tests for command line (#47)

- Moved from PyDNS to dnspython
- Tests can now be run without having to start a log-server first (#6)
- MailRequest objects are now wrappers around Python's
  ``email.message.Message`` class. (#40)

  - Deserializing incoming messages is now done in a slightly more lazy fashion
  - Also allows access to the "pristine" ``Message`` object without having to
    back-convert
  - Header setting now replaces by default (#44)

- End support of Python 2.6 (#42)
- Settings no longer limited to per app "config" module (#38)
- Allow ``salmon.server.Relay`` to talk to LMTP servers (#41)
- Make ``LMTPReceiver`` the default in the prototype app (#48)
- Properly work around ``SMTPReceiver`` bug caused by an assumption about
  Python's ``smtpd`` module that should not have been made (#48)

  - This means that Salmon will no longer accept multiple RCPT TOs in the same
    transaction over SMTP. Consider using ``LMTPReceiver`` instead as it does
    not have this restriction.

- Python 3 support (#7)

  - You'll now need ``setuptools`` to install (this won't be a problem for
    those upgrading)
  - No more support for Windows - it never worked for production on that
    platform anyway

- Don't catch ``socket.error`` when delivering messages via
  ``salmon.server.Relay`` (#49)

- Bind to port ``0`` during tests as this lets the OS choose a free port for us
  (#51)
- Wrote some documentation (#33)

Earlier Releases
================

Sorry, we didn't keep a changelog prior to Salmon 3.0!
