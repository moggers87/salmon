Routing
=======

Routing in Salmon works via two mechanisms: the ``@route`` decorator and a
finite state machine.

The ``@route`` decorator uses the ``to`` header to determine if the handler
matches the message - in a similar way to how web frameworks configure URL
handlers.

The finite state machine uses the ``from`` header as a key to keep track of a
given sender. For example, a mailing list application might have two handlers
with same ``@route``, one handler for those who are subscribed and another for
those who are not.

Here's a breif overview of how Salmon decides which of your application's
handlers should process the message:

1. Match all handlers whose ``@route`` decorator matches the ``to`` header
2. Iterate over these and call the following:
    i. any handlers that have been marked as ``@stateless``
    ii. the first (and only) stateful handler. If it returns a handler
        reference, the state for that sender will be updated.
3. If no valid handlers were found, the message is sent to the undeliverable
    queue

Using Routes
------------

.. TODO


The Finite State Machine
------------------------

.. TODO
