Receivers
=========

Salmon comes with a number of receivers

Asyncio based receivers
-----------------------

Salmon's default receivers based on `aiosmtpd <https://github.com/aio-libs/aiosmtpd>`__.

.. note::
   Although these receivers use Asyncio, your handlers are executed in a
   separate thread to allow them to use synchronous code that is easier to
   write and maintain.

:class:`~salmon.server.AsyncLMTPReceiver`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:class:`~salmon.server.AsyncSMTPReceiver`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Asyncore based receivers
------------------------

Salmon's original receivers based on Python's ``smtpd`` library.

:class:`~salmon.server.LMTPReceiver`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:class:`~salmon.server.SMTPReceiver`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. warning::
   This receiver is not suitable for use on an Internet facing port. Try
   `AsyncSMTPReceiver`_ instead.

Other receivers
---------------

:class:`~salmon.server.QueueReceiver`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
