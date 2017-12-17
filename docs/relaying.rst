Relaying
========

Mail servers don't just receive mail, they also send mail too. Salmon can do
all the required relaying itself, but better performance you might want to use
your frontend mailserver to do this for you.

Creating Relay Objects
----------------------

By default, a :class:`~salmon.server.Relay` object expects to find a mailserver
on IP ``127.0.0.1``, port ``25``. The ``host`` and ``port`` keyword arguments
control this::

    # probably in your boot.py
    from salmon.server import Relay
    other_host_relay = Relay(host="example.com", port=123)

You can also specify other options such as username, password, and encryption
options. See :class:`salmon.server.Relay` for more information.

If you wish to do do all the relaying in Salmon and not delegate to another
mailserver, simply set ``host`` to ``None``::

    resolving_relay = Relay(host=None)

This will mean that the MX host for the recipient of the message will be used
for delivery.

Creating Responses
------------------

Creating responses with HTML and plaintext parts is quite common, so Salmon has
the :func:`~salmon.view.respond` function to render via templates::

    from salmon.view import respond

    from salmon.view import respond

    variables = {"user": "user1", ...}
    message = respond(variables,
        Body="plaintext_template.txt",
        Html="html_template.html",
        To="me@example.com",
        From="you@example.com",
        Subject="Test")

``plaintext_template.txt`` and ``html_template.html`` should be paths that your
template engine can find and load. Keyword arguments other than ``Body`` and
``Html`` will be passed directly to :class:`~salmon.mail.MailResponse`. Keyword
arguments will also be formatted with the contents of variables::

    >>> message = respond(variables, Subject="Hello %(user)s", ...)
    >>> print(message["Subject"])
    Hello user1

Salmon needs to be configured to use a template engine::

    # in your boot.py
    from salmon import view
    from jinja2 import Environment, FileSystemLoader

    template_path = "/path/to/templates/"
    view.LOADER = Environment(loader=FileSystemLoader(template_path))

.. note::
    You don't have to use Jinja 2, but whatever you set ``salmon.view.LOADER``
    to it must have a method `get_template`` which must return an object with
    the method ``render``. Mako and Django template engines have classes that
    implement these methods. Refer to their documentation for more information.

Delivery
--------

Once you have a :class:`~salmon.mail.MailResponse` object ready to send and a
:class:`~salmon.server.Relay` object, delivery is quite simple::

    new_message = MailResponse()
    my_relay.deliver(new_message)

.. note::
    If you've ``host`` to ``None``, be sure to have something in place to
    catch exceptions and retry.


You can also override ``To`` and ``Form`` too::

    my_relay.deliver(new_message, To="someone@example.com", From="another@example.com")
