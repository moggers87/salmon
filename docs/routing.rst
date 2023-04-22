Routing
=======

Routing in Salmon works via two mechanisms: the ``@route`` decorator and a
finite state machine.

The ``@route`` decorator uses the recipient to determine which handlers match
the message - in a similar way to how web frameworks configure URL handlers.

The finite state machine uses the sender as a key to keep track of which of the
matched handlers the message should be given to. For example, a mailing list
application might have two handlers with same ``@route``, one handler for those
who are subscribed and another for those who are not.

Here's a brief overview of how Salmon decides which of your application's
handlers should process the message:

1. Match all handlers whose ``@route`` decorator matches the ``to`` header
2. Iterate over these and call the following

    - any handlers that have been marked as ``@stateless``
    - the first (and only) stateful handler. If it returns a handler
       reference, the state for that sender will be updated.

    Keep in mind these could be called in any order and you should not rely on
    them being called in a particular order.

3. If no valid handlers were found, the message is sent to the undeliverable
   queue

Using Routes
------------

The :class:`~salmon.routing.route` decorator takes a regex pattern as its first
argument and then capture groups as keyword arguments:

.. code-block:: python

    from salmon.routing import route


    @route("(list_name)-(action)@(host)",
        list_name="[a-z]+", action="[a-z]+", host="example\.com")
    def START(message, list_name=None, action=None, host=None)
        ....


For example, a message to ``salmon-subscribe@example.com`` would match this
handler, but a message to ``salmon@example.com`` would not - even if ``START``
was our only handler.

It's quite usual to multiple handlers decorated with the same ``route`` - we'll
cover why in the next section. To save typing, you can have your handler routed
exactly like another:

.. code-block:: python

    from salmon.routing import route_like


    @route_like(START):
    def CONFIRM(message, list_name=None, action=None, host=None):
        ....


Again, a message to ``salmon-subscribe@example.com`` would match this handler,
but a message to ``salmon@example.com`` would not. How to control which handler
out of the two is ultimately used to process a message is discussed in the next
section.


The Finite State Machine
------------------------

The finite state machine is how Salmon knows where to process a message, even
when multiple handlers have routes that match the recipient. Before we explain
how that is done, let's look at how to control the finite state machine.

First of all, let's flesh out the examples from the previous section. These
examples will call some functions defined in ``myapp`` which we won't define as
how they work is not important.:

.. code-block:: python

    from salmon.routing import route, route_like
    from myapp.utils import (
        confirmed_checker,  # returns True or False
        confirm_sender,  # adds sender to subsciber list
        send_confirmation,  # sends a confirmation email
        post_message,  # posts a message to the given mailing list
    )


    @route("(list_name)-(action)@(host)",
        list_name="[a-z]+", action="[a-z]+", host="example\.com")
    def START(message, list_name=None, action=None, host=None)
        if action == "subscribe" and not confirmed_checker(message.from):
            send_confirmation(message.from)
            return CONFIRM
        elif action == "post":
            post_message(message, list_name)
            return
        else:
            # unknown action
            return


    @route_like(START):
    def CONFIRM(message, list_name=None, action=None, host=None):
        confirm_sender(message.form)
        return START


When a message from a previously unknown sender is received, it will be matched
against a ``START`` handler with the correct ``route``. In our example, if
``action`` is ``"subscribe"`` then the handler returns ``CONFIRM`` - which is
another handler. The next time a message from this sender is received, the
``CONFIRM`` handler will process the message and the state will return to
``START`` (as ``CONFIRM`` always returns ``START``).

.. note::

    The ``CONFIRM`` handler wouldn't reset the state to ``START`` in a real
    application, but examples have been kept short to make them easier to
    understand.

State storage in Salmon is controlled by encoding the current module and sender
to a string, then using that string as a key for a ``dict``-like object that
stores the state as the value for that key. For example, the state storage for
our application might look like this:

.. code-block:: pycon

    >>> from salmon.routing import Router
    >>> print(Router.STATE_STORE.states)
    {
        "['myapp', 'user1@example.com']": <function CONFIRM at 0x7f64194fa320>,
        "['myapp', 'user2@example.com']": <function START at 0x7f64194fa398>
    }

Handlers and thread safety
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::

    This only applies to Salmon v4.0.0 or later. Previous version of Salmon
    used a lock on every handler call, which reduced performance.

Salmon uses threads to process multiple incoming messages more efficiently.
This means it is important to write handlers in a thread-safe manner. If you're
already familiar with frameworks such as Django, this shouldn't be a surprise
to you.

Some APIs are already thread-safe, such as saving mail to a Maildir. Others can
be made thread-safe by being mindful of which parts are designed to be accessed
concurrently and which can't (such as SQLAlchemy's ``Session`` objects, as
noted in `their documentation
<https://docs.sqlalchemy.org/en/14/orm/session_basics.html#is-the-session-thread-safe>`_.
However, there are occasions where there is no way make the API work with
concurrent execution. For these situations you can either:

#. Use ``threading.RLock`` from Python's threading library on a block of unsafe code:

    .. code-block:: python

       from threading import RLock

       from salmon.routing import route

       LOCK = RLock()
       HEADER_LOG_FILENAME = "somefile.txt"


       @route(".*")
       def START(message):
           # do something that's thread-safe
           header_names = "\n".join(message.keys())

           # now append to a file
           with LOCK:
               with open(HEADER_LOG_FILENAME, "a") as log_file:
                   log_file.write(header_names)
                   log_file.write("\n")

    This approach has the advantage that it can have a lesser impact on
    performance, although that does come at the cost of code complexity.

#. Use the :func:`~salmon.routing.locking` decorator to lock on every call to that handler:

    .. code-block:: python

       from salmon.routing import locking, route

       HEADER_LOG_FILENAME = "somefile.txt"


       @route(".*")
       @locking
       def START(message):
           # do something that's thread-safe
           header_names = "\n".join(message.keys())

           # now append to a file
           with open(HEADER_LOG_FILENAME, "a") as log_file:
               log_file.write(header_names)
               log_file.write("\n")

    Here, the whole function is called from within a lock rather than just the
    thread-unsafe parts.


Stateless Processing
^^^^^^^^^^^^^^^^^^^^

If you don't require states for one or more of your handlers, the decorator
:func:`~salmon.routing.stateless` will make sure the state machine is
completely bypassed on the way in (but you can still return handles to affect
the sender's state):

.. code-block:: python

    from salmon.routing import stateless, route


    @route("admin@example.com")
    @stateless
    def ADMINS(message):
        # forward the email to admins
        ....


Implementing State Storage
^^^^^^^^^^^^^^^^^^^^^^^^^^

The default state storage :class:`~salmon.routing.MemoryStorage` is only
intended for testing as it only stores state in memory - states will be lost.
For small installations, :class:`~salmon.routing.ShelveStorage` will save state
to disk and be performant enough. Add the following lines to your ``boot.py``
to use it:

.. code-block:: python

    from myapp.models import ShelveStorage
    Router.STATE_STORAGE = ShelveStorage()

Larger installations will be required to write their own state storage. Any
popular database that can provide some sort of atomic get and set should be
capable. For example, Django's ORM could be used:

.. code-block:: python

    # in your models.py
    from django.db import models
    from salmon.routing import StateStorage, ROUTE_FIRST_STATE


    # this model is incomplete, but should give you a good start
    class SalmonState(models.Model):
        key = models.CharField()
        sender = models.CharField()
        state = models.CharField()


    class DjangoStateStorage(StateStorage):
        def get(self, key, sender):
            try:
                state = SalmonState.objects.get(key=key, sender=sender)
                return state.state
            except SalmonState.DoesNotExist:
                return ROUTE_FIRST_STATE

        def set(self, key, sender, state):
            SalmonState.objects.update_or_create(
                key=key, sender=sender, kwargs={"state": state}
            )

        def clear(self):
            SalmonState.objects.all().delete()


    # at the end of boot.py
    from myapp.models import DjangoStateStorage
    Router.STATE_STORAGE = DjangoStateStorage()


.. note::

    This example is incomplete, it's only there to give an idea of how to
    implement a state storage class.

.. note::

    State storage must be thread-safe. In this example, all the calls to
    Django's ORM are either atomic (e.g. ``SalmonState.objects.get()``) or Django
    automatically wraps them in a transaction (e.g.
    ``SalmonState.objects.all().delete()``)
