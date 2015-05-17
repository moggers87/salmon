=====================
Deploying OneShotBlog
=====================

These instructions follow from :doc:`Deploying Salmon Level 1 <deploying_salmon>` and you should follow those first before attempting these.  If you run into
problems with these instructions, then `email the salmon``librelist.com <mailto:salmon``librelist.com>`_ mailing list for help.


Step 5: Setting Up The OneShotBlog
----------------------------------

Let's see if we can setup the OneShotBlog example from the Salmon source the
way it is on the `oneshotblog.com <http://oneshotblog.com>`_ site.  We'll need a
few more modules installed with easy_install:

<pre class="code">
$ cd $DEPLOY/LAMSON
$ easy_install markdown
$ easy_install mock
$ easy_install spambayes
</pre>


Let's grab the 0.9.3 source from `PyPI <http://pypi.python.org/pypi/salmon/0.9.3>`_ so we can get at the OSB example source:

<pre class="code">
$ cd $DEPLOY/source
$ wget http://pypi.python.org/packages/source/l/salmon/salmon-0.9.3.tar.gz
$ tar -xzf salmon-0.9.3.tar.gz
$ cd salmon-0.9.3/examples/osb
</pre>

Now we hit a slight snag.  OSB is using
`SpamBayes <http://spambayes.sourceforge.net/>`_ to do spam filtering, but you
probably will have a broken setup and would need to configure a ton of stuff to
get it working.  For now we're, just going to cheat, since it looks like
SpamBayes has problems with trying to iterate the keys in a bsddb under *some*
Python builds.  To avoid the problem, we're just going to edit
``app/handlers/comment.py`` to remove the line with ``spam_filter``:

<pre class="code prettyprint">
@route("(user_id)-AT-(domain)-(post_name)-comment@(host)")
# DELETE THIS LINE IN app/handlers/comments.py
@spam_filter(SPAM['db'], SPAM['rc'], SPAM['queue'], next_state=SPAMMING)
def START(message, user_id=None, post_name=None, host=None, domain=None):
    comment.attach_headers(message, user_id, post_name, domain)
    confirmation.send(relay, "comment", message, "mail/comment_confirm.msg", locals())
    return CONFIRMING
</pre>

The spam filtering does work, but SpamBayes is difficult to get working in such
a small test run.

You are now sitting in the OSB example code, so you can fire up the logger
server and run the unit tests to make sure everything is working:

<pre class="code">
$ mkdir logs
$ mkdir run
$ mkdir app/data/posts
$ salmon log
$ nosetests
</pre>


You should get two errors you can ignore for now:

<pre class="code">
..............
======================================================================
FAIL: handlers.comments_tests.test_spam_sent_by_unconfirmed_user
----------------------------------------------------------------------
Traceback (most recent call last):
    ...
-------------------- >> begin captured logging << --------------------
root: WARNING: Attempt to post to user 'spamtester@somehost.com' but user doesn't exist.
--------------------- >> end captured logging << ---------------------

======================================================================
FAIL: handlers.comments_tests.test_spam_sent_by_confirmed_user
----------------------------------------------------------------------
Traceback (most recent call last):
    ...
-------------------- >> begin captured stdout << ---------------------
run/posts count after dever 1
run/posts count after dever 2

--------------------- >> end captured stdout << ----------------------
-------------------- >> begin captured logging << --------------------
root: WARNING: Attempt to post to user 'spamtester@somehost.com' but user doesn't exist.
--------------------- >> end captured logging << ---------------------

----------------------------------------------------------------------
Ran 25 tests in 1.363s
</pre>

Those are just fine since you don't have PyEnchant installed and aren't using
the spam filtering.

Step 6: Run OneShotBlog Example
-------------------------------

Now you're running the logger server and have your unit tests going, and
hopefully you can fix anything that you run into by now.  All you need now is
to run the whole setup and try it out:

<pre class="code">
$ salmon start
$ salmon start -pid run/queue.pid -boot config.queue
$ salmon start -pid run/forward.pid -boot config.forward
</pre>

With all this gear running you should be able to look in the ``logs/salmon.log``
and ``logs/logger.log`` to see what's going on.  You'll see the following
activity:

* Forwarding receiver taking mail that couldn't be delivered and forwarding it to the logger server.
* The queue receiver pulling messages off run/posts and either delivering them as comments or updating the index.
* The rest of salmon processing mail and doing its job of feeding these two or just sending emails.

bq. If you want to see the configuration for these two other servers look in ``config/queue.py`` and
``config/forward.py`` or better yet, diff them against ``config/boot.py`` to see what's really different.

You should also check to see that they are really running:

<pre class="code">
$ ps ax | grep salmon
29438   ??  S 0:05.78 python salmon log
29605   ??  S 0:00.63 python salmon start
29612   ??  S 0:00.19 python salmon start -pid run/queue.pid -boot config.queue
29617   ??  S 0:00.34 python salmon start -pid run/forward.pid -boot config.forward
</pre>

Step 7: Playing With OneShotBlog
--------------------------------

Now we get to play with it.  Salmon comes with a web server that you can run to
do simple testing so start up a second window/terminal and do this:

<pre class="code">
$ cd projects/salmon/deploy/
$ . activate LAMSON
(LAMSON) $ cd source/salmon-0.9.3/examples/osb/
(LAMSON) $ salmon web -basedir app/data
Starting server on 127.0.0.1:8888 out of directory 'app/data'
</pre>

Now hit `http://localhost:8888/ <http://localhost:8888/>`_ with your browser and
see the junk left over from your test runs.  Most of those posts won't actually
exist, so let's make a fake one for now.

You can forget about this web server window for now, and go back to your LAMSON
window to do this with mutt:

# mutt -F muttrc to get it going with a fake setup.
# Send an email to first.blog@oneshotblog.com  (m is the key).
# You'll get a confirmation back, reply to it.
# You'll get a welcome message, but this message isn't in the index yet.  You can go look at it directly though.
# Send *another* email, this time to my.new.post@oneshotblog.com.
# No confirmation this time, just a message saying it was completed.
# *Now* go look at the index (might take a few seconds, up to 10).
# Click on the post title and go look at it.
# Right click on the [send comment] link and copy the email address.
# Go back to mutt and send an email to that address, this will post a comment to that post.
# Reply to the comment confirmation email, this should be the only one you get.
# In about 10 seconds you'll see your comment show up.

With that you have fully tested out the OneShotBlog example.  All that remains
would be a full deployment in a for-real situation, which is what we'll do
next.


Step 8:  Running On Port 25 For Real
------------------------------------

The only problem with testing out the OneShotBlog with your own email client is
that you need to trick your computer into thinking your localhost address is
also oneshotblog.com.  To do that, open your /etc/hosts file and make whatever
changes you need to have localhost be oneshotblog.com also.

You'll know you've got it right when you can point your browser at
`oneshotblog.com <http://oneshotblog.com/>`_ and see your ``salmon web`` window
display log messages showing you click around.

bq.  Remember to undo this or you might be annoyed later.

Next, you'll need to stop salmon and restart it to use port 25.  This will be a
problem if you have another server running on port 25, so make sure you turn
that server off for now.

bq.  I hope you aren't doing this on a live site where that's a problem.

<pre class="code">
$ salmon stop
$ vim config/settings.py
</pre>

At this point you'll want to change the receiver_config to look like this in
``config/settings.py``:

<pre class="code prettyprint">
receiver_config = {'host': 'localhost', 'port': 25}
</pre>

Then you'll want to restart salmon so that it drops privilege to your user
after grabbing that port.  Easiest way to find out what your user id (uid) and
group id (gid) are is to use Python:

<pre class="code prettyprint">
Python 2.6.2 (r262:71600, Jun  8 2009, 00:44:56)
[GCC 4.0.1 (Apple Inc. build 5490)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>> import os
>>> os.getuid()
500
>>> os.getgid()
500
>>> ^D
</pre>

This shows that I'm uid 500 and gid 500, so now I can start my server:

<pre class="code">
$ sudo salmon start -uid 500 -gid 500
$ sudo chown -R zedshaw ./
</pre>

That last command just makes sure that salmon didn't accidentally change the
permission of a stray file or queue to ``root``.

With that you should be running your salmon server as your user rather than as
root, but still bound to port 25.  Here's how to check:

<pre class="code">
$ ps aux | grep salmon | grep root
</pre>

If you don't see anything printed out, then you're safe.  If you see something
running as root, then you've got some work to do.


Conclusion
----------

I'll leave it to you to actually get your mail client to talk to this
OneShotBlog and working.  If you have problems, look at all the files in
``logs/`` and also use the ``salmon queue`` command to inspect the different queues
in the ``run/`` directory.

At this point, you should know enough about setting up a salmon server and
configuring a real application (warts and all).  You should also have learned
how to get a clean Python installation that you can use no matter what your
native OS does to Python, even if it's retarded and renames python to Python
for no apparent reason.
