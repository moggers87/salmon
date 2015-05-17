==========================
Filtering Spam With Salmon
==========================

Salmon supports initial use of the
`SpamBayes <http://spambayes.sourceforge.net/>`_ spam filter library for filtering
spam.  What Salmon provides is a set of easy to use decorators that you attach
to your state functions which indicate that you want spam filtered.  It also
uses the default SpamBayes configuration files and database formats as you
configure, so if you have an existing SpamBayes setup you should be able to use
it right away.


Using salmon.spam
-----------------

Salmon gives you a simple decorator to place on any state functions that should
block spam.  Typically you do *not* want spam filtering on your entire
application, since that would prevent legitimate registrations and put too much
burden on your system.  It's better to put spam filtering on the "insider"
parts, and to have confirmation emails on "outsider" pieces.

Instead, what you want is to indicate that your "choke points" are filtering
spam using
`salmon.spam.spam_filter <http://salmonproject.org/docs/api/salmon.spam.spam_filter-class.html>`_
so that when a spam is received they are put into a "spam black hole".

Here's an trivial example where the user is in the POSTING state, and you want
everything to work like normal, but if they spam then you flip them into a
SPAMMING state.

<pre class="code prettyprint">
@route(".+")
def SPAMMING(message):
    # the spam black hole
    pass

@route("(anything)@(host)", anything=".+", host=".+")
@spam_filter("run/spamdb", "run/.hammierc", "run/spam", next_state=SPAMMING)
def POSTING(message, **kw):
    print "Ham message received."
    ...
</pre>

The line to look at is obviously the ``spam_filter`` line, which tells Salmon that you will:

# Use the SpamBayes training database ``run/spamdb`` for the detection.
# Use the SpamBayes ``run/.hammierc`` file for your config (optional and ignored if it is not there).
# Use ``run/spam`` as the dumping ground for anything classified as spam.
# The next_state to transition to if they send a spam message.  *This is optional, but very helpful.*

With this, the ``spam_filter`` then wraps your state function, and every message
is fed to SpamBayes.  If SpamBayes says it's spam then Salmon will dump it into
your ``run/spam`` and transition to SPAMMING *without running your POSTING
state*.

Once you are in this new ``SPAMMING`` state (or any state you like) you can do
whatever you want.  You can leave them there, or you can have an external tool
that let's you un-block someone.  Pretty much any spam handling scheme you want
is available.

Since your spam is placed into a queue you can inspect it later and check for
any accidentally miscategorized mail, then use the SpamBayes tools to retrain
for the misdetection.

bq.  Salmon only classifies mail that is marked as actual spam by looking at
the 'X-Spambayes-Classification' header and seeing if it starts with 'spam'.
If it is 'unsure' or 'ham' it will let it through.



Effectiveness
-------------

`I've <http://zedshaw.com/>`_ been running a variant of this since the middle of
May 2009 and it works great.   The code I run is a custom version that fits the
weirdness of my email setup but the principles are the same.  I'm currently
using the above spam filtering, some gray listing, and a few other tricks to
block most of my incoming spam.

With all the spam block measures I've managed to cut down my spam to about 2-3
a day out of about 100-200 I receive.  The majority of the "spam" that gets
through is actually email that's classified as "unsure" which I then use to
retrain SpamBayes to make it stronger.

However, that's my personal server, so in the case of a Salmon application
you'll want to be careful that your spam blocking activities don't prevent too
much legitimate use.

Changing What "Spam" Means
--------------------------

You can also change how spam is determined by sub-classing
`salmon.spam.spam_filter <http://salmonproject.org/docs/api/salmon.spam.spam_filter-class.html>`_
and doing your own implementation of the ``spam`` method.


Using SpamBayes
---------------

An important point about SpamBayes is that it comes with all the command line
tools you need to configure and train your database using a corpus of spam you
might have.  All Salmon needs to do is read this database to determine if it is
spam or not.

With mutt, I save the message to "=spam", which places the spam in Mail/spam
along with all of the others.  Then I run this command:

<pre class="code">
sb_mboxtrain.py -s ~/Mail/spam -d run/spamdb
</pre>

This goes through the spam mailbox, and any emails that SpamBayes has *not*
already classified get used for training.

SpamBayes comes with other commands you can "read
about":http://spambayes.sourceforge.net/docs.html on their site (if you can
find it).


Autotraining
------------

Salmon doesn't support "autotraining" directly, since it's not clear in each
situation what is obviously spam.  In my personal setup I know that any email
not for registered users is obviously spam, so I can autotrain those.

If you want to implement autotraining for a part of your application, then look
at the API for
`salmon.spam.Filter <http://salmonproject.org/docs/api/salmon.spam.Filter-class.html>`_
and simply use it in the right state function.


Configuration
-------------

Finally, the above sample code is not the best way to configure the spam filter.
It's better to put the configuration in ``config/settings.py`` and simply reference
it from there.

In your ``config/settings.py`` put this:

<pre class="code prettyprint">
SPAM = {'db': 'run/spamdb', 'rc': 'run/spamrc', 'queue': 'run/spam'}
</pre>

Then change your handler code to be this:

<pre class="code prettyprint">
from config.settings import SPAM

@spam_filter(SPAM['db'], SPAM['rc'], SPAM['queue'], next_state=SPAMMING)
def START(message, ...):
   # this is the better way to do your config
</pre>

With that you can then change up the configuration as needed in
your deployments without having to change your code.


