Mail Objects
============

:class:`~salmon.mail.MailRequest` and :class:`~salmon.mail.MailResponse`
objects are two ways that Salmon represents emails. They provide a simplified
interface to Python's own :mod:`email` package.

.. _mail-request:

MailRequest
-----------

:class:`~salmon.mail.MailRequest` objects are given to your message handlers
when a new email comes in.

To/From properties
^^^^^^^^^^^^^^^^^^

``To`` and ``From`` are populated by the ``RCPT TO`` and ``MAIL FROM`` commands
issued by the sender to Salmon. If you're using
:class:`~salmon.server.QueueReceiver`, these properties will be ``None``.


Headers
^^^^^^^

Headers are accessed a dict-like interface::

    >>> print(message["Subject"])
    My Subject

Headers are also case insensitive::

    >>> print(message["Subject"] == message["sUbJeCt"])
    True

Methods ``keys`` and ``items`` are also supported::

    message.keys()  # ["To", "From", "Subject"]
    message.items()  # [("To", "me@example.com"), ...]

.. note::
    Emails can contain multiple headers with the same name. This is quite
    common with headers such as ``Received``, but is completely valid for any
    header. Be aware of this when iterating over header names from the ``keys``
    method!

Headers can be set too::

    >>> message["New-Header"] = "My Value"
    >>> print(message["New-Header"])
    My Value

.. warning::
    When headers are added this way, any previous values will be overwritten.
    This should be no surprise to new users, but might trip up users of
    Python's ``email`` package.

Bodies
^^^^^^

The ``body`` property isn't that smart, it just returns the body of the first
MIME part of the email. For emails that only have one part or are non-MIME
emails this is fine, but there's no guarantee what you'll end up with if your
email is a multipart message.

For MIME emails, call the ``walk`` method to iterate over each part::

    >>> for part in message.walk():
    ...    # each part is an instance of MimeBase
    ...    print("This is a %s part" % part["Content-Type"])
    This is a multipart/alternative part
    This is a text/html part
    This is a text/plain part

See :ref:`mail-base` for more details.

Detecting Bounce Emails
^^^^^^^^^^^^^^^^^^^^^^^

Detecting bounced emails is quite important - especially if you're sending as
well as receiving::

    >>> if message.is_bounce():
    ...    print("Message is a bounced email!")

``is_bounce`` also takes a ``threshold`` argument that can be used to fine-tune
bounce detection::

    >>> if message.is_bounce(0.5):
    ...   print("I'm more certain that this is a bounced email than before!")


Python Email-like API
^^^^^^^^^^^^^^^^^^^^^

If you require an API that is more like Python's :mod:`email` package, then the
``base`` property holds a reference to the corresponding :ref:`mail-base` object::

    mail_base = message.base

.. _mail-response:

MailResponse
------------

:class:`~salmon.mail.MailResponse` objects can be created to send responses via
:class:`salmon.server.Relay`. They can either be created directly::

    from salmon.mail import MailResponse

    msg_html = "<html><body>Hello!</body></html>"
    msg_txt = "Hello!"
    message = MailResponse(
        Body=msg_txt,
        Html=msg_html,
        To="me@example.com",
        From="you@example.com",
        Subject="Test")

Or via :func:`salmon.view.respond`::

    from salmon.view import respond

    variables = {"user": "user1", ...}
    message = respond(variables,
        Body="plaintext_template.txt",
        Html="html_template.html",
        To="me@example.com",
        From="you@example.com",
        Subject="Test")

Headers and accessing a Python Email-like API are the same as they are for
:ref:`mail-request`.

Attachments
^^^^^^^^^^^

Attachments can be added via the ``attach`` method::

    filename = "image.jpg"
    file = open(filename, "r")
    message.attach(filename=filename, content_type="image/jpeg", data=file.read())

.. _mail-base:

MailBase
--------

:class:`~salmon.encoding.MailBase` contains most of the logic behind
:ref:`mail-request` and :ref:`mail-response`, but is less user-friendly as it
exposes more of what an email can actually do.

Headers
^^^^^^^

Headers are accessed by the same dict-like interface as :ref:`mail-request` and
:ref:`mail-response`. It also has some additional methods for dealing with multiple
headers with the same name.

To fetch all values of a given header name, use the ``get_all`` method::

    >>> print(mail_base.get_all("Received"))
    ["from example.com by localhost...", "from localhost by..."]
    >>> print(mail_base.get_all("Not-A-Real-Header"))
    []

To add a multiple headers with the same name, use the ``append_header`` method::

    >>> print(mail_base.keys())
    ["To", "From", "Subject"]
    >>> mail_base.append_header("Subject", "Another subject header")
    >>> print(mail_base.keys())
    ["To", "From", "Subject", "Subject"]

.. warning::
    Be cautious when using this feature, especially with headers that will be
    displayed to the user such as Subject. There's no telling what email
    clients will do if presented with multiple headers like this. This feature
    is better suited to machine read headers such as Received.

Content Encoding
^^^^^^^^^^^^^^^^

The ``content_encoding`` property contains the parsed contents of various
content encoding headers::

    >>> print(mail_base["Content-Type"])
    text/html; charset="us-ascii"
    >>> print(mail_base.content_encoding["Content-Type"])
    ("text/html", {"charset": "us-ascii"})

Content encoding headers can also be set via this property::

    >>> ct = ("text/html", {"charset": "utf-8"}
    >>> mail_base.content_encoding["Content-Type"] = ct
    >>> print(mail_base["Content-Type"])
    text/html; charset=uft-8

Body
^^^^

The ``body`` property returns the fully decoded payload of a MIME part. In the
case of a "text/\*" part this will be decoded fully into a Unicode object,
otherwise it will only be decoded into bytes.

Accessing Python ``email`` API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As Salmon builds upon Python's :mod:`email` API, the underlying
:class:`email.message.Message` instance is available via the ``mime_part``
property::

    email_obj = mail_base.mime_part

Thus, if you don't want to bother with all the nice things Salmon does for you
in your handlers, you can bypass all that loveliness quite easily::

    @route_like(START)
    def PROCESS(message, **kwargs):
        # grab Message object from incoming message
        email_obj = message.mail_base.mime_part
