=============
Confirmations
=============


You never know who's going to send an email to your Salmon application.  It may
be a real person, or a spam bot.  Currently most of the spam bots aren't very
intelligent (probably because they haven't discovered Salmon yet) so a simple
easy way to weed out the randomness is to confirm people at important "choke
points" in your application.

Salmon provides a simple API in
`salmon.confirm <http://salmonproject.org/docs/api/salmon.confirm-module.html>`_
to help you send out and verify confirmation emails.  You provide a storage
class for keeping track of who you're expecting to confirm, a template for your
message to send, and it does the rest.  It's even advanced enough to keep the
original email around so you can resend it after the confirmation.


The General Theory
------------------

The confirmation API assumes a few things about how you're doing your
confirmations:

# You want them to reply to an email to confirm.
# The address they reply to confirm has a "target" to differentiate it from other parts of your application that needs confirmation.
# The address they reply to also has a hex formatted randomly generated UUID for security, and your storage can handle that length.
# You want to store the message they sent so you can get it back after they confirm.

With those fairly reasonable assumptions you only need to then setup the
confirmation API in your ``config/settings.py`` file and use it in your handlers,
preferrably at your ``START`` state and anywhere else that you need
to validate the user before they do something destructive.


Simplest Usage
--------------

The most basic usage of the
`salmon.confirm <http://salmonproject.org/docs/api/salmon.confirm-module.html>`_
API is to put it in your ``config/settings.py`` and then access it in your
handlers.  You configure it like this:

<pre class="code prettyprint">
from salmon import confirm

...
CONFIRM_STORAGE=confirm.ConfirmationStorage()
CONFIRM = confirm.ConfirmationEngine('run/pending')
</pre>

This puts a variable in your settings.py that you can access from your handlers
to craft and verify the confirmation messages.

bq. By default uses a simple in-memory dict to store the confirmations.  That's
fine for testing and an initial deploy, but you'll probably want to switch to a
permanent form of storage for later.  Further on in this document you'll see
how.

Next, you need to use it in your ``START`` state, and then in a ``CONFIRMING``
state.  Here's a simple example:

<pre class="code prettyprint">
from config.settings import relay, CONFIRM

@route("start@(host)")
def START(message, host=None):
    CONFIRM.send(relay, "start", message, "mail/start_confirm.msg", locals())
    return CONFIRMING

@route("start-confirm-(id_number)@(host)", id_number='[a-z0-9]+')
def CONFIRMING(message, id_number=None, host=None):
    original = CONFIRM.verify('start', message['from'], id_number)

    if original:
        welcome = view.respond(locals(), "mail/welcome.msg",
                           From='noreply@%(host)s',
                           To=message['from'],
                           Subject="Welcome")
        relay.deliver(welcome)

        return PROTECTING
    else:
        logging.warning("Invalid confirm from %s", message['from'])
        return CONFIRMING
</pre>

Here's how the above code works:

# First we import the CONFIRM variable so we can use it.
# In our ``START`` handler (which is accepts start@(host)) we use the API to send out the confirmation message they should reply-to.  Notice how we give a "start" target as the second argument, this is important.
# Then we transition to CONFIRMING and wait for them to reply to that message.
# The user then replies to the message we sent, so we handle the CONFIRMING state.  Notice that we are handling "start-confirm-(id_number)" as the initial message, with "start" being the target (2nd parameter) from our above ``CONFIRM.send`` call.
# In CONFIRMING we use the ``CONFRIM.verify`` method to validate that it's from the right person, to the right target ("start") and that they got the secret (id_number) right.
# Finally, if it's right we send them a welcome message, and if it's not we just ignore the message.

An alternative to ignoring the failed confirmation from them is to cancel it
and go back to the START state for them.  The danger with that method though is
a spam bot will get into a loop where you are sending them constant
confirmation messages in a loop between START and CONFIRMING.  It's best to
drop it, and maybe provide a "cancel" mechanism.


Using Shelf Storage
-------------------

Other than a few other methods, there's only a need to change the storage.  The
simplest change is to provide a dict-like interface to the
`salmon.confirm.ConfirmationEngine <http://salmonproject.org/docs/api/salmon.confirm.ConfirmationEngine-class.html>`_
to store.  Easiest available is the Python
`shelf <http://docs.python.org/library/shelve.html>`_ module which gives a dict
interface to various key/value storage backends.

To use one, just change your code in ``config/settings.py`` to be like this:

<pre class="code prettyprint">
import shelve
from salmon import confirm

...
CONFIRM_STORAGE=confirm.ConfirmationStorage(db=shelve.open("run/confirmationsdb"))
CONFIRM = confirm.ConfirmationEngine('run/pending', CONFIRM_STORAGE)
</pre>

All you do is create a
`salmon.confirm.ConfirmationStorage <http://salmonproject.org/docs/api/salmon.confirm.ConfirmationStorage-class.html>`_
and give the ``db=`` parameter a dict it can use.  Everything else will be the
same.

bq.  There might be thread issues with this, and it will definitely fail if you use mulitple processes.  See the next
section on using a Django Model.


Using A Django ORM Model
------------------------

In the `librelist.com <http://librelist.com/>`_ example code you'll find that it
stores the confirmations in the Django model in the ``webapp/librelist``
directory.  This is actually easily setup, so first read :doc:`Hooking Into
Django <hooking_into_django>` to learn how to access a Django ORM.
After that, you write a simple version of ``ConfirmationStorage`` that would look
something like this:

<pre class="code prettyprint">
from webapp.librelist.models import Confirmation

class DjangoConfirmStorage():
    def clear(self):
        Confirmation.objects.all().delete()

    def get(self, target, from_address):
        confirmations = Confirmation.objects.filter(from_address=from_address,
                                                list_name=target)
        if confirmations:
            return confirmations[0].expected_secret, confirmations[0].pending_message_id
        else:
            return None, None

    def delete(self, target, from_address):
        Confirmation.objects.filter(from_address=from_address,
                                                list_name=target).delete()

    def store(self, target, from_address, expected_secret, pending_message_id):
        conf = Confirmation(from_address=from_address,
                            expected_secret = expected_secret,
                            pending_message_id = pending_message_id,
                            list_name=target)
        conf.save()
</pre>

This is from Librelist, so you see we just import the ``Confirmation`` model and
then wrap it with the ``get``, ``delete``, ``set``, and ``clear`` methods that
``ConfirmationEngine`` needs to run.

For completeness, here's what the Django ``Confirmation`` model looks like:

<pre class="code prettyprint">
class Confirmation(models.Model):
    from_address = models.EmailField()
    request_date = models.DateTimeField(auto_now_add=True)
    expected_secret = models.CharField(max_length=50)
    pending_message_id = models.CharField(max_length=200)
    list_name = models.CharField(max_length=200)

    def __unicode__(self):
        return self.from_address
</pre>


Final step is to configure it in your ``config/settings.py`` thusly:

<pre class="code prettyprint">
from salmon import confirm

...

from app.model.confirmation import DjangoConfirmStorage
CONFIRM = confirm.ConfirmationEngine('run/pending', DjangoConfirmStorage())
</pre>

That's all there is to it.  This is actually a nice setup because you can use
the Django Admin to manage it during your first deployments.


Other ORM
---------

For other ORM systems simply use the same pattern as the Django example above.
You just create a similar model, wrap it with your own version of
``ConfirmationStorage`` and plug it into the ``ConfirmationEngine`` you use.


Targets
-------

The only other thing to understand is why the API has a "target" parameter.
Let's look at the call to CONFIRM.send again:

<pre class="code prettyprint">
CONFIRM.send(relay, "start", message, "mail/start_confirm.msg", locals())
</pre>

The "start" string as the second parameter acts as a the target. It says that
this user needs to confirm for the "start" target when they do their reply.
That's why the ``route`` on ``CONFIRMING`` is then like this:

<pre class="code prettyprint">
@route("start-confirm-(id_number)@(host)", id_number='[a-z0-9]+')
</pre>

You could also make the above a pattern, for example in the Librelist
confirmations we're confirming that the user is joining a certain
mailing list:

<pre class="code prettyprint">
@route('(list_name)-confirm-(id_number)@(host)')
def CONFIRMING_SUBSCRIBE(message, list_name=None, id_number=None, host=None):
    original = CONFIRM.verify(list_name, message['from'], id_number)
    ...
</pre>

This way, the user could have multiple simultaneous confirmations going for
different lists and they won't step on eachother.

Without this differentiator, you'd have to either restrict users to just one
confirmation at a time, or you'd end up getting the data all confused.


Confirming Off A Web Link
-------------------------

If you want people to go to a web link instead of simply replying, then you have to do the
following:

# Either write your own version, or subclass ``ConfirmationEngine`` so that it uses an address they can't reply to.
# Make sure you use an ORM that can access your database and store both the confirmation info, and each users's state.
# When the user hits the link you give them and does whatever you need, use the web framework's ORM to validate their confirmation.
# Once your web framework has validated their confirmation, then change their state *in Salmon's state* using *your web framework ORM* out of CONFIRMING and into the next state.

Assuming you're doing this all with Python it should be fairly trivial.

Confirm Only By Web Is Bad
--------------------------

I would advise against this method though, since it doesn't really confirm that
the email address you received worked.  One of the purposes of doing a
confirmation email exchange is to make sure that this person can both *send*
and *receive*.  If you have to point them at your web site, consider having
this process instead:

# Their first interaction with your service sends out an email that sends them to a web page, and transitions them to a ``CONFIRMING`` state *but do not send them a confirmation reply address from Salmon.*  You'll actually "delay" this until they fill out your web forms.
# In your web framework, you have them fill out forms and such, and then send them the *real* confirmation message using Salmon.  Since the Confirmation API is Python you could do this directly in any Python web framework.  You're basically moving the call to ``CONFRIM.send`` from your ``START`` handler into the web framework.
# Then your web framework will have sent them a real confirmation email, not just a link, so when they reply, continue with the usual Salmon confirmation process described above.

Doing it this way ends up being a good balance between too many clicks and replies, but too few to confirm that the end user can actually reply
to email you send them.


The Pending Queue
-----------------

You should also notice in the above examples that the original message is
stored in a "pending queue" and then given back to you later.  This is handy
for either finishing their original request without further intervention, or
inspecting what they original wanted to do.  In the original Librelist code I
would take their first message, confirm them, and then pull it out of the
pending queue to send it on.  This turned out to not work because socially
people "subscribe" with a garbage first message, but technically it worked
great.

bq. You may want to periodically go through this queue and purge any messages that aren't found in the ConfirmationsStorage.  Probably with a simple Python script and a cronjob.


Conclusion
----------

The Salmon confirmation API encapsulates a pattern for confirming potential
users.  Feel free to suggest improvements to the API if you find further
patterns that are needed.

