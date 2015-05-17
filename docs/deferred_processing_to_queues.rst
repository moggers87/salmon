=============================
Deferred Processing To Queues
=============================

As of the 0.9.2 release there is preliminary support for deferring handling of
a mail message to a queue for another process to deal with in a separate
handler.  This support is rough at this time, but still useful and not too
difficult to configure.  As the feature gets more use it will improve and
hopefully turn into a generic "defer to queue" system in Salmon.

What is meant by "defer to queue" is simply that you take messages your state
function receives and you dump them into a maildir queue.  You then have
another separate process read from this queue and do the real work.
Potentially you could have many processes deal with this work, and they could
even be on multiple computers.


A More Concrete Example
-----------------------

Imagine that you have a blog posting system and you want to update a big "front
page index" that shows recent posts by your users.  However, you don't want to
generate this index on *every* blog post users make, since that could involve
expensive computation and hold up other threads that need to deal with more
urgent email.

The solution is to do the minimum quick processing you can in your POSTING
state function, and then use the
`salmon.queue.Queue <http://salmonproject.org/docs/api/salmon.queue.Queue-class.html>`_
to queue up messages meant for "front page indexing".  Here's how that code
might go:

<pre class="code prettyprint">
@route("(post_name)@osb\\.(host)")
def POSTING(message, post_name=None, host=None):
    # do the regular posting to blog thing
    name, address = parseaddr(message['from'])
    post.post(post_name, address, message)
    msg = view.respond('page_ready.msg', locals())
    relay.deliver(msg)

    # drop the message off into the 'posts' queue for later
    index_q = queue.Queue("run/posts")
    index_q.push(message)

    return POSTING
</pre>

You can see that you just drop it into the queue with @push(message)@ and it's
done.  What you don't see is how this then gets picked up by another process to
actually do somehing with this email.

Configuring A config/queue.py
-----------------------------

In Salmon you are given control over how your software boots, which gives you
the ability to configure extra services how you need.  By default the @salmon
gen`` command just outputs a basic ``config/boot.py`` and ``config/testing.py@ file
so you can get working, and these will work for most development purposes.

In this tutorial you get to write a new boot configuration and tell Salmon how
to use it.  We'll be copying the original boot file over first:

<pre class="code">
$ cp config/boot.py config/queue.py
</pre>

Next you want to edit this file so that instead of running an
`SMTPReceiver <http://salmonproject.org/docs/api/salmon.server.SMTPReceiver-class.html>`_
it will use a
`QueueReceiver <http://salmonproject.org/docs/api/salmon.server.QueueReceiver-class.html>`_
configured to pull out of the ``run/posts`` queue you are using in your ``POSTING``
handler.


<pre class="code prettyprint">
...
# where to listen for incoming messages
settings.receiver = QueueReceiver(settings.queue_config['queue'],
                                  settings.queue_config['sleep'])

settings.database = configure_database(settings.database_config, also_create=False)

Router.defaults(**settings.router_defaults)
# NOTE: this is using a different handlers variable in settings
Router.load(settings.queue_handlers)
Router.RELOAD=True
...
</pre>

I've removed the code above the ... and below it since it's the same in the two
files.  Notice that you have a ``QueueReceiver`` now, and that you are telling
the
`Router <http://salmonproject.org/docs/api/salmon.routing.RoutingBase-class.html>`_
that it will use ``settings.queue_handlers`` for the list of handlers to load and
run.

You now add these two lines to your ``config/settings.py``:

<pre class="code prettyprint">
...
# this is for when you run the config.queue boot
queue_config = {'queue': 'run/posts', 'sleep': 10}

queue_handlers = ['app.handlers.index']
</pre>

The ``queue_config`` variable is read by the ``config/queue.py`` file for the
``QueueReceiver`` and the ``queue_handlers`` is fed to the ``Router`` as described
above.

Writing The Index Handler
-------------------------

You now have to write a new handler that is in ``app/handlers/index.py`` so that
this ``config.queue`` boot setup will load it and run it whenever a message hits
the ``run/queue``.  Here's the code:

<pre class="code prettyprint">
from salmon import queue
from salmon.routing import route, stateless
import logging


@route("(post_name)@osb\\.(host)")
@stateless
def START(message, post_name=None, host=None):
    logging.debug("Got message from %s", message['from'])
</pre>

This simple demonstration will just log what messages it receives so you can
make sure it is working.

There are two points to notice about this handler.  First, it is marked
``stateless`` because it will run independent of the regular Salmon server, and
you don't want its parallel operations to interfere with your normal server's
state operations.  Second, it uses a ``Router.defaults`` named ``post_name`` that
you would add to your ``config.settings.router_defaults``.

Once you have all this slightly complicated setup done you are ready to test
it.

bq. Also note that the examples in the `source releases </releases/>`_ have code
that does a deferred queue similar to this.  Go look there for more code to
steal.

Running Your Queue Receiver
---------------------------

Run your logger and salmon server like normal:

<pre class="code">
$ salmon log
$ salmon start
</pre>

Next, go look in your logs and make sure it works by running your unit
tests:

<pre class="code">
$ nosetests
................
----------------------------------------------------------------------
Ran 16 tests in 1.346s

OK
</pre>

Your logs should look normal, but now you should see some files in the
``run/posts/new`` directory:

<pre class="code">
$ ls run/posts/new/
1244080328.M408474P3147Q4.mycomputer.local
</pre>

That's the results of your ``POSTING`` handler putting the messages it receives
into your ``run/posts`` maildir queue.

Finally, you'll want to run your queue receiver:

<pre class="code">
$ salmon start -boot config.queue -pid run/queue.pid
</pre>

If you're running the code given above then you should see this in the
``logs/salmon.log`` file:

<pre class="code">
...
DEBUG:root:Sleeping for 10 seconds...
DEBUG:root:Pulled message with key:
'1244080328.M408474P3147Q4.zed-shaws-macbook.local' off
DEBUG:root:Message received from Peer: 'run/posts', From:
'sender-1244080328.22@sender.com', to To
['test.blog.1244080328@osb.test.com'].
DEBUG:root:Got message from sender-1244080328.22@sender.com
DEBUG:root:Message to test.blog.1244080328@osb.test.com was handled by
app.handlers.index.START
</pre>

Which means your queue receiver is running.  You could *in theory* run as many
of these as you wanted, as long as their handlers are stateless.

When you're done you can stop the whole setup with the following command:

<pre class="code">
$ salmon stop -ALL run
Stopping processes with the following PID files:
['run/log.pid', 'run/queue.pid', 'run/smtp.pid']
Attempting to stop salmon at pid 3092
Attempting to stop salmon at pid 3157
Attempting to stop salmon at pid 3096
</pre>

Further Advanced Usage
----------------------

This configuration is debatable whether it is very usable or not, but it works
and will improve as the project continues.  To give you some ideas of what you
can do with it:

# Defer activity to other machines or processes.
# Receive messages from other mail systems that know maildir.
# Deliver messages to other maildir aware systems.
# Process messages from a web application, and possibly even generic work.

It might also be possible to actually make your state functions transition to
the queue handler states by simply having the function return the
``module.FUNCTION`` that should be next.  Take care with this though as it means
your end user's actions are effectively blocked for that event until the next
run of the queue receiver.

Call For Suggestions
--------------------

Feel free to offer suggestions in improving this setup (or even better code).
