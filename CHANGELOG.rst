3.0-dev
=======

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

  - You'll now require ``setuptools`` to install (this won't be a problem for
    those upgrading)
  - No more support for Windows - it never worked for production on that
    platform anyway

- Don't catch ``socket.error`` when delivering messages via
  ``salmon.server.Relay`` (#49)

Earlier Releases
================

Sorry, we didn't keep a changelog prior to Salmon 3.0!
