================
Bounce Detection
================

Salmon supports intelligent bounce detection with its
`salmon.bounce <http://salmonproject.org/docs/api/salmon.bounce-module.html>`_
module.  The bounce handling is based on a probability that, depending on found
headers, the message is a bounce.  It then gives you a nice clean interface to
check who it's from, the originating SMTP server, the error messages, and any
human readable messages.

How Bounces Actually Work
=========================

Figuring out how a bounce is actually handled is a bit difficult because the
majority of the information available is written by people who know very little
of SMTP server operations.  When the average programmer thinks of handling a
bounce, she usually has one of these concepts in mind:

# The message could not be delivered, so the remote SMTP server sent back a bounce message.
# The message could not be delivered, so the local SMTP server sent back a bounce message.
# The message could not be delivered, so the recipient's email client sent back a bounce message.
# The message could not be delivered, so Salmon crafted a bounce message.

Obviously logically you can't have the recipient's email client send you a
bounce unless the user does something weird (and incredibly annoying).  This
makes sense because the message was ``not delivered``.  How can the email client
send back a bounce if they don't receive the message.

bq. Yes, some clients do support sending bounces, but very few people use this
feature.  If you do please talk about it as one more edge case to deal with.

Next Salmon can't craft the bounce messages for you because Salmon is simply
trying to deliver outgoing mail to a smart-host.  Salmon does nothing but ask
the smart-host (your local SMTP server) to deliver, and then waits for a
response.  That means Salmon is not sending you any kind of bounce unless you
write code to make it do that.

That leaves only two options for ``who`` is really sending the bounce message:
the remote MTA or the local MTA.  The truth is it's a little bit of both.

Your Local MTA Is A Person
--------------------------

How a bounce works in practice involves two SMTP servers:  your local
smart-host, and the remote server that it tries to connect to for delivery.
The message you actually get in salmon is from the ``local`` server, and usually
an address ``at`` that local server.  It does not come from the remote server,
but inside your bounce will be a message and status indicators from the remote
server indicating why it bounced.

What happens is your local server attempts to deliver, and the remote server
rejects it for some reason.  Now your local server is supposed to try again in
certain situations, but after a certain number of rejections or failures it
crafts a bounce message.  That bounce message is then returned to your ``salmon``
server based on the ``envelope`` header of the message (more on that later).

Now, what's inside this message?  Well, it's a oddly nested barely standardized
pile of random other messages.  This is the frustration with bounce handling.
You pretty much either have to use a probability mechanism (like Salmon does)
or you have to craft your bounce handling for your very specific local server
and any other possible servers you talk with.  Even then you can have problems
dealing with bounces reliably.

Inside this description is an important concept to understand:

bq. Salmon does NOT process bounces from the remote MTA or the remote user in
any way. Salmon process bounces from the ``local`` SMTP server.

This is important because if you try to use the bounce message as if it comes
from the remote user, then you'll accidentally put your ``local`` server into a
state that prevents you from processing future bounce messages.

If you did not get that, reread this whole section again until moving forward.

"Hard" vs. "Soft"
-----------------

Another complexity in dealing with bounces is the concept of "Hard" vs. "Soft"
bounces.  My opinion is that the distinction is fairly retarded since it is
almost entirely unreliable and has no meaning to someone trying to handle a
bounce.

In popular terminology the main difference is this:

* Hard bounce means that person does not exist, so I can not sell him any more crap and need to remove him (maybe).
* Soft bounce means that person still exists, but my marketing bullshit didn't get through, I should try again 10 or 15 more times until he gets my important message about winning the lottery.

You may be laughing, or screaming various pedantic specifics, but the above two
distinctions are both how many email services look at bounces, and how most
malicious mail users view them.

For the mail services, leaking a hard or soft bounce is a security problem
because it tells a malicious sender if that address is a valid person, why the
sender was blocked, and how they can work around it.  This is why many of the
error messages you get back are vague and mostly lies.  The major email
services just don't want to give you any information that you can use to
circumvent their anti-spam measures.

bq. The services that have the strictest anti-spam measures also have the most
nasty disgusting spam on the web pages displaying user's mail.  Yahoo is both
the worst for erroneously blocking email and for showing the worst most tricky
spam all over every square inch of their mail service.

How does this relate to your Salmon application?  It basically says that you
should treat bounces as being basically soft bounces all the time, and then
tune your rules heuristically over time as you run into more and more.

VERP
----

The final topic to touch on before getting into how Salmon handles bounces is
one of VERP.  Remember in the description of bounce handling above I said that
your ``local`` MTA sends the bounce message back to the ``envelope from`` not the
From in the headers (well, most ones will).  Because of this you can have a
From in the envelope that is only replied to when there's a bounce, and then
put the real From in the headers for normal processing.

This is effectively what "Variable Envelope Return
Path":http://en.wikipedia.org/wiki/Variable_envelope_return_path does to
process bounce messages.  Rather than attempt to parse the body of a bounce
message, VERP rewrite the From address so that when a bounce is returned, you
only have to process the returned address to see what the original was.

Salmon could potentially support this, but it has several problems for generic
bounce handling which meant that actually parsing bounce bodies was a better
option.

Using Salmon's Bounce Handling
------------------------------

Using Salmon's bounce handling is fairly simple.  It involves the following
process:

# Import a special decorator ``bounce_to`` from `salmon.bounce <http://salmonproject.org/docs/api/salmon.bounce-module.html>`_
# Create two (or one) handlers to deal with bounces.
# Place the decorator on any ``START`` entry points to your handlers that can receive bounces, pointing them at your handlers.
# Handle the bounces in your handlers, making sure to return back to the ``START`` state for the local MTA (remember, the local MTA is a person for bounce handling).

Here's some simple code that does exactly this by just ignoring bounces from
the `myinboxisnota.tv <http://myinboxisnota.tv/>`_ example::

.. code-block:: python

    from config.settings import BOUNCES
    from salmon.routing import route
    from salmon.bounce import bounce_to

    @route(".+")
    def IGNORE_BOUNCE(message):
        bounces = queue.Queue(BOUNCES)
        bounces.push(message)
        return START

    @route("start@(host)")
    @bounce_to(soft=IGNORE_BOUNCE, hard=IGNORE_BOUNCE)
    def START(message, host=None):
        CONFIRM.send(relay, "start", message, "mail/start_confirm.msg", locals())
        return CONFIRMING

This example is stripped down from the real code so you can see what's going
on.  If we walk through this you can see what happens:

# First we import the ``BOUNCES`` variable from ``config.settings`` which is just the queue we want to dump bounces into.
# We then create a special handler named ``IGNORE_BOUNCE`` that accepts a message to anything in its ``route`` and just puts the message in the ``BOUNCES`` queue.
# This ``IGNORE_BOUNCE`` handler then immediately returns ``START`` so we go back to the START state.
# On the ``START`` state you'll see that we have our ``bounce_to`` declaration that points for ``hard`` and ``soft`` bounces at ``IGNORE_BOUNCE``.
# This decorator wraps your handler in a little check that, if the message is a bounce, your ``START`` state won't get called, and instead your ``IGNORE_BOUNCE`` state will.

That is pretty much all you need to deal with to re-route bounces somewhere else.
You can also redirect them to a totally different handler, which is exactly
what the `librelist.com <http://librelist.com/>`_ example does.

How It Works
------------

How does Salmon figure out that something is a bounce?  What Salmon does is it assumes bounces will have some or all of these
headers:

<pre class="code prettyprint">
BOUNCE_MATCHERS = {
    'Action': re.compile(r'(failed|delayed|delivered|relayed|expanded)', re.IGNORECASE | re.DOTALL),
    'Content-Description': re.compile(r'(Notification|Undelivered Message|Delivery Report)', re.IGNORECASE | re.DOTALL),
    'Diagnostic-Code': re.compile(r'(.+);\s*([0-9\-\.]+)?\s*(.*)', re.IGNORECASE | re.DOTALL),
    'Final-Recipient': re.compile(r'(.+);\s*(.*)', re.IGNORECASE | re.DOTALL),
    'Received': re.compile(r'(.+)', re.IGNORECASE | re.DOTALL),
    'Remote-Mta': re.compile(r'(.+);\s*(.*)', re.IGNORECASE | re.DOTALL),
    'Reporting-Mta': re.compile(r'(.+);\s*(.*)', re.IGNORECASE | re.DOTALL),
    'Status': re.compile(r'([0-9]+)\.([0-9]+)\.([0-9]+)', re.IGNORECASE | re.DOTALL)
}
</pre>

The problem traditionally with parsing a bounce message was that, while you
need to find all of these headers, there was no real standard as to how the
messages in the bounce message are structured.  From my
`postfix <http://www.postfix.org/>`_ server the bounce message is a sequence of
about 6 nested attachments containing other messages, and sometimes the nesting
goes three deep.

Rather than rely on this structure (which changes all the time) or that these
headers are always present (they aren't), Salmon takes a probabilistic approach
based on the number of headers and properly formatted values it finds in ``all``
nested attachments.  The process goes something like this:

# Traverse all the possible nested attachments.
# Try to find each header in the attachment.  If it's found add a point.
# If the header is found, use the regex associated with it (above) to try to match the value.
## If the value matches, then keep the regex captures for later.  Add another point.
# For each header found, and any regex captures that matched the bodies, put them into an internal dict for analyzing the bounce information.
# Finally, calculate a probability score that is the total number of BOUNCE_MATCHERS * 2.0 / points.

In general, if a message is found that has a 0.3 or higher bounce probability
then it is considered a bounce message and you can look at it.  The ``bounce_to``
decorator has a threshold you can adjust if you want to be more or less strict.

The final result of this processing (which is actually very fast) is that any
calls to ``MailRequest.is_bounce`` will either return True or False, and then
after you call is_bounce you can access the ``MailRequest.bounce`` attribute to
analyze the information.  That information is captured and cooked into a
`BounceAnalyzer <http://salmonproject.org/docs/api/salmon.bounce.BounceAnalyzer-class.html>`_
object.


What It Looks Like To Receive One
---------------------------------

It's also instructive to see what it looks like when Salmon processes a bounce
message.  Here's the `librelist.com <http://librelist.com/>`_ server processing
a bounce message:


<pre class="code">
2009-08-21 13:43:47,223 - root - DEBUG - Pulled message with key:
'1250876622.V8e00I219de0M128371' off

2009-08-21 13:43:47,231 - root - DEBUG - Message received from Peer:
'/var/mail/vhosts/librelist.com/delivery/', From: u'"SPAMMER"
<SPAMMER``hotmail.com>', to To [u'salmon``librelist.com'].

2009-08-21 13:43:47,251 - routing - DEBUG - Matched u'salmon@librelist.com'
against START.

2009-08-21 13:43:47,332 - routing - DEBUG - Message to
set([u'salmon@librelist.com']) was handled by app.handlers.admin.START

2009-08-21 13:43:57,367 - root - DEBUG - Pulled message with key:
'1250876627.V8e00I219661M719350' off

2009-08-21 13:43:57,381 - root - DEBUG - Message received from Peer:
'/var/mail/vhosts/librelist.com/delivery/', From:
u'MAILER-DAEMON@librelist.com (Mail Delivery System)', to To
[u'salmon-confirm-74e2ca94b24a4be18da277f4666a6494@librelist.com'].

2009-08-21 13:43:57,410 - routing - DEBUG - Matched
u'salmon-confirm-74e2ca94b24a4be18da277f4666a6494@librelist.com' against START.

2009-08-21 13:43:57,431 - routing - DEBUG - Message to
set([u'salmon-confirm-74e2ca94b24a4be18da277f4666a6494@librelist.com']) was
handled by app.handlers.admin.START
</pre>

These log messages show the following interaction:

# SPAMMER``hotmail.com tried to spam the salmon``librelist.com mailing list.
# They were required to subscribe, so Salmon sent them a confirmation mail.
# That message bounced, so Postfix sent back a bounce message from MAILER-DAEMON@librelist.com to Salmon.
# This message from MAILER-DAEMON is a bounce, so the librelist code handled it on the START state, NOT the CONFIRMING_SUBSCRIBE state.
# Internally, librelist looked up the target user and just zapped them.

That shows how the bounce doesn't come from SPAMMER@hotmail.com nor any server
at hotmail.com, but instead from MAILER-DAEMON@librelist.com.  You could also
get messages from a remote MTA, but if they were found to be bounce messages
then that remote MTA would be treated like your own MTA.

Gettting Bounce Information From BounceAnalyzer
-----------------------------------------------

The `BounceAnalyzer <http://salmonproject.org/docs/api/salmon.bounce.BounceAnalyzer-class.html>`_
does the work of figuring out additional useful information you can use to
determine what to do with the bounce.  It looks at the final headers that are
scanned in the above process and pulls out important information everyone
needs.  The list of information you can get is:

* primary_status -- The main status number that determines hard vs soft.
* secondary_status -- Advice status.
* combined_status -- the 2nd and 3rd number combined gives more detail.
* remote_mta -- The MTA that you sent mail to and aborted.
* reporting_mta -- The MTA that was sending the mail and has to report to you.
* diagnostic_codes -- Human readable codes usually with info from the provider.
* action -- Usually 'failed', and turns out to be not too useful.
* content_parts -- All the attachments found as a hash keyed by the type.
* original -- The original message, if it's found.
* report -- All report elements, as salmon.encoding.MailBase raw messages.
* notification -- Usually the detailed reason you bounced.

But, refer to the documentation for more accurate listings.  An important
feature is that the status codes are parsed and converted into a standard list
available in ``salmon.bounce`` based on their numeric values.  Rather than parse
the details given by the remote MTA, you just use the number codes to get a
human readable output.

The best way to see all that's possible is to take a glance at the Salmon unit
test for the BounceAnalyzer:

<pre class="code prettyprint">
def test_bounce_analyzer_on_bounce():
    bm = mail.MailRequest(None,None,None, open("tests/bounce.msg").read())
    assert bm.is_bounce()
    assert bm.bounce
    assert bm.bounce.score == 1.0
    assert bm.bounce.probable()
    assert_equal(bm.bounce.primary_status, (5, u'Permanent Failure'))
    assert_equal(bm.bounce.secondary_status, (1, u'Addressing Status'))
    assert_equal(bm.bounce.combined_status, (11, u'Bad destination mailbox address'))

    assert bm.bounce.is_hard()
    assert_equal(bm.bounce.is_hard(), not bm.bounce.is_soft())

    assert_equal(bm.bounce.remote_mta, u'gmail-smtp-in.l.google.com')
    assert_equal(bm.bounce.reporting_mta, u'mail.zedshaw.com')
    assert_equal(bm.bounce.final_recipient,
                 u'asdfasdfasdfasdfasdfasdfewrqertrtyrthsfgdfgadfqeadvxzvz@gmail.com')
    assert_equal(bm.bounce.diagnostic_codes[0], u'550-5.1.1')
    assert_equal(bm.bounce.action, 'failed')
    assert 'Content-Description-Parts' in bm.bounce.headers

    assert bm.bounce.error_for_humans()
</pre>

Here you can see that you can figure out if the bounce is hard vs. soft, get a
human description, access status codes of various flavors, get the remote MTA's
name, the reporting MTA (your local), who it was originally for
(final_recipient), and even access the raw ``bounce.headers`` if that's not good
enough.

Augmenting The Matchers
-----------------------

Another advantage of this method of processing the bounces is that if your SMTP
server crafts something that hasn't been handled, then you can augment the
matchers being used.  Simply update the ``salmon.bounce.BOUNCE_MATCHERS`` dict
with your new ones and make sure to update ``salmon.bounce.BOUNCE_MAX`` to be 2
times that.

The status codes are also available in the same way.  Refer to the source for
more information.

One tricky part of Salmon's bounce handling is that it does assume a certain
structure for the BounceAnalyzer to get at the internal details.  This
structure is the one used by Postfix, and it should be the same for other
servers.  However, if you run into a structural difference, report the results
back so the handling can be improved.

A More Complete Example
-----------------------

Finally, the `librelist.com <http://librelist.com/>`_ example code has a much more
complete example of using bounces to disable users and shift their state.
Rather than describe it in detail here, I'll simply point you at the "source
releases":/releases/ so you can see it for yourself.  Look in
``examples/librelist/app/handlers/bounce.py`` to see how it all works.

In fact, studying how this is triggered from the rest of the librelist example
is a great way to learn how to use Salmon in an advanced fashion.  Study well.

Conclusion
----------

Salmon bounce handling is very advanced and can deal with a wide range of
scenarios.  It should work with a wide range of bounce styles and other
servers, but feel free to report your own experiences and differences.


