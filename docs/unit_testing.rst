============
Unit Testing
============


Salmon provides the
`salmon.testing <http://salmonproject.org/docs/api/salmon.testing-module.html>`_
to help with writing unit tests.  It doesn't do everything for you, but does
enough that you can TDD your email interactions with pretend users.  It
includes features for checking messages get delivered to queues, checking
spelling, and running things through a fake or real relay.

The Log server
--------------

The first thing you need to do for testing is to run the "log server":

<pre class="code prettyprint">
$ salmon log
</pre>

The log server acts as the smart relay host you've configured in your ``config/settings.py``
file by default.  What it does is take all emails that your Salmon application
"sends out" and redeposits them into ``run/queue``.  This queue directory is then also
used by ``salmon.testing`` for checking that emails were sent out.  When anything goes
wrong, you can look in this directory and see what is getting sent out.

bq. An alternative to this setup would be to have all of the sending/routing/relaying done
internal to the whole testing framework, similar to how ``salmon.testing.RelayConversation`` works.
However, I found that this made testing that your server actually sends proper emails much
too difficult.


Test Organization
-----------------

Salmon organizes tests into directories that match the things you're testing:

<pre class="code">
librelist $ ls -l tests/
total 16
drwxr-xr-x  6 zedshaw  staff   204 Aug 19 17:01 handlers
drwxr-xr-x  8 zedshaw  staff   272 Aug 18 15:50 model
drwxr-xr-x  3 zedshaw  staff   102 Aug 18 15:50 templates
</pre>

In most of the projects I've only rarely used template tests, but I'll cover
them below.  Model tests make sure that any ``app.model`` classes work right, and
handler tests make sure that any ``app.handler`` classes work.  Nice and simple.

You can add any other directories you want to this, and you can also use
doctests if you want.  This comes free with
`nosetests <http://somethingaboutorange.com/mrl/projects/nose/0.11.1/>`_ and is
very handy.


Handler Tests
-------------

We'll use an example from the `librelist.com <http://librelist.com/>`_ code base
that validates that a user can subscribe, unsubscribe, and post a message to a
mailing list.  This test was primarily written in a TDD style, since generally
interactions and usability testing works better
`TDD <http://en.wikipedia.org/wiki/Test-driven_development>`_ style.

First you have a common preamble of modules that you need to include:

<pre class="code prettyprint">
from nose.tools import *
from salmon.testing import *
from config import settings
import time
from app.model import archive, confirmation

</pre>

Right away you notice we just include everything from ``nose.tools`` and
``salmon.testing`` so that we can use it directly.  Yes, this violates Python
style guidelines, but practicality is more important than dogmatic slavery to
supposed standards.

After that we include the ``config.settings``, and two modules from ``app.model`` that we'll
use to check that everything was working.

bq. Notice that we don't include anything from ``app.handlers`` directly.  These tests are meant
to be from the perspective of a user interacting with the handler via emails.

Once we have that we do a little setup to clear set some common variables and clear
out some queues we'll need to check:

<pre class="code prettyprint">
queue_path = archive.store_path('test.list', 'queue')
sender = "sender-%s@sender.com" % time.time()
host = "librelist.com"
list_name = "test.list"
list_addr = "test.list@%s" % host
client = RouterConversation(sender, 'Admin Tests')


def setup():
    clear_queue("run/posts")
    clear_queue("run/spam")
</pre>

Most of these are just variables used in tests later, but the big one is the
``client`` variable.  It's a
`salmon.testing.RouterConversation <http://salmonproject.org/docs/api/salmon.testing.RouterConversation-class.html>`_
class that lets you simulate delivering email to your Salmon project.

bq.  There's also a
`salmon.testing.TestConversation <http://salmonproject.org/docs/api/salmon.testing.TestConversation-class.html>`_
class that actually uses your real ``config/settings.py`` to connect to a Relay.
This isn't used so much, but is intended for running "smoke tests" against a
newly deployed server.

With that we're ready to write out first handler test:

<pre class="code prettyprint">
def test_new_user_subscribes_with_invalid_name():
    client.begin()

    client.say('test-list@%s' % host, "I can't read!", 'noreply')
    client.say('test=list@%s' % host, "I can't read!", 'noreply')
    clear_queue()

    client.say('unbounce@%s' % host, "I have two email addresses!")
    assert not delivered('noreply')
    assert not delivered('unbounce')

    client.say('noreply@%s' % host, "Dumb dumb.")
    assert not delivered('noreply')
</pre>

This is the longest of the tests, and shows all the various things you can do
with the ``salmon.testing`` gear.  Here's what we're doing in order:

# Call ``client.begin`` to clear out queues and state and start fresh.
# Use ``client.say`` to send an email from that client to your Salmon application.  Notice that you configured the RelayConversation to pretend to be one person with each email getting the same subject line.
# Use ``salmon.testing.clear_queue`` when you want to make sure the queue is clean.
# Use ``salmon.testing.delivered`` to check if a certain message from someone is in the queue.

With that you can do pretty much everything you need to send an email and make
sure you get proper replies.

Here's another example:

<pre class="code prettyprint">
def test_new_user_subscribes():
    client.begin()
    msg = client.say(list_addr, "Hey I was wondering how to fix this?",
                     list_name + '-confirm')
    client.say(msg['Reply-To'], 'Confirmed I am.', 'noreply')
    clear_queue()
</pre>

Notice in this example we have a fourth parameter ``list_name + '-confirm'`` and
we get a ``msg`` back from our call to ``client.say``.  This basically combines
``client.say`` with ``delivered`` to do it in one shot.  Very commonly, you'll want
to say something to your server and make sure you got a certain response, and
then do something with that response.  This is how you do that.

We then use this '-confirm' email message to actually subscribe the fake user.

Finally, here's two more examples:

<pre class="code prettyprint">
def test_existing_user_unsubscribes():
    test_new_user_subscribes()
    msg = client.say(list_name + "-unsubscribe@%s" % host,
        "I would like to unsubscribe.", 'confirm')
    client.say(msg['Reply-To'], 'Confirmed yes I want out.', 'noreply')

def test_existing_user_posts_message():
    test_new_user_subscribes()
    msg = client.say(list_addr, "Howdy folks, I was wondering what this is?",
                     list_addr)
    # make sure it gets archived
    assert delivered(list_addr, to_queue=queue(queue_path))
</pre>

In ``test_existing_user_unsubscribes`` what we do is call
``test_new_user_subscribes`` to go through that process again, and then we chain
off that to do an unsubscribe.  There's really nothing new here other than that
little trick.

In ``test_existing_user_posts_message`` we do the usual send a message and expect
a reply, but then we *also* make sure that this message was delivered to the
archiver queue.

Apart from those methods and techniques, there's really nothing more to doing a
handler test.  The only additional thing would be using
`assert_in_state <http://salmonproject.org/docs/api/salmon.testing-module.html#assert_in_state>`_
to make sure that your handler is in a particular state.  I'd recommend against
doing that too much in a handler test, since it will make your tests brittle.
I only do it when the state is very important, such as when checking that they
are in a SPAMMING or BOUNCING state that I need to enforce.



Model Tests
-----------

There's less functionality available in ``salmon.testing`` for doing your models.  The theory
is that your models will be classes, modules, and ORM that you need to perform the majority
of your storage and analysis.  Since has very little to do with email you probably won't
use ``salmon.testing`` as much.

About the only things you might use are APIs for checking that queues get certain messages
in them, and that certain users are in certain states.

Here's a quick example from `librelist.com <http://librelist.com>`_ again that tests how
archives work:

<pre class="code prettyprint">
from nose.tools import *
from salmon.testing import *
from salmon.mail import MailRequest, MailResponse
from app.model import archive, mailinglist
import simplejson as json
import shutil

queue_path = archive.store_path('test.list', 'queue')
json_path = archive.store_path('test.list', 'json')

def setup():
    clear_queue(queue_path)
    shutil.rmtree(json_path)

def teardown():
    clear_queue(queue_path)
    shutil.rmtree(json_path)

def test_archive_enqueue():
    msg = MailResponse(From="zedshaw``zedshaw.com", To="test.list``librelist.com",
                       Subject="test message", Body="This is a test.")

    archive.enqueue('test.list', msg)
    assert delivered('zedshaw', to_queue=queue(queue_path))
</pre>

This is the usual initial setup, and then some extras to make sure that the `JSON archives <http://librelist.com/browser/>`_ is working.  You'll notice that we hand construct various messages, call methods on the ``app.model.archive`` module, and then use ``delivered`` to make sure they're correctly delivered.


Template Tests
--------------

Typically you really can only test that your templates are spelled right, or that your templates
render when given certain locals.  I've found that automated testing of templates isn't incredibly
useful yet, so the only one I've written is from the `oneshotblog <http://oneshotblog.com/>`_ example:

<pre class="code prettyprint">
from nose.tools import *
from salmon.testing import *
from salmon import view
import os
from glob import glob

def test_spelling():
    message = {}
    original = {}
    for path in glob("app/templates/mail/*.msg"):
        template = "mail/" + os.path.basename(path)
        result = view.render(locals(), template)
        spelling(template, result)
</pre>

This uses ``salmon.testing.spelling`` to make sure that each template renders and
that it is spelled correctly.  This uses
`PyEnchant <http://www.rfk.id.au/software/pyenchant/>`_ to do the checking, which
turns out to be rather annoying.  If you are interested in improving the
template testing setup, then feel free to talk about your ideas on "the salmon
mailing list":mailto:salmon@librelist.com (but bring code, talk is cheap).


Conclusion
----------

Hopefully you'll be able to develop your application using good testing techniques with
the ``salmon.testing`` API.  If you find additional testing patterns that could be included
then `talk about them on the salmon mailing list <mailto:salmon@librelist.com>`_ to see
if they're general enough for others.

