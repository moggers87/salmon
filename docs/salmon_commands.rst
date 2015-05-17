=========================
Available Salmon Commands
=========================

<p>The following is also available by running <b>salmon help</b> and you can get the
help for each individual command with <b>salmon help -for COMMAND</b> replacing
COMMAND with one of these listed below.</p>

<p>The format for the printed options show default options as an actual setting,
and required options as a CAPITALIZED setting you must give.  For example, in the
<b>send</b> command:</p>

<pre class="code">
salmon send -port 8825 -host 127.0.0.1 -debug 1 -sender EMAIL -to EMAIL -subject STR -body STR -attach False
</pre>

<p>
The options -port, -host, -debug, and -file have default settings, but -sender,
-to, -subject and -body require a STRing or EMAIL.  Notice also that -file
defaults to False which you can change by just including -file (that
toggles it true).
</p>


<h2>salmon blast</h2>

<pre class="code">
Given a maildir, this command will go through each email
and blast it at your server.  It does nothing to the message, so
it will be real messages hitting your server, not cleansed ones.
</pre>

<h2>salmon cleanse</h2>

<pre class="code">
Uses Salmon mail cleansing and canonicalization system to take an
input maildir (or mbox) and replicate the email over into another
maildir.  It's used mostly for testing and cleaning.
</pre>

<h2>salmon gen</h2>

<pre class="code">
Generates various useful things for you to get you started.

salmon gen -project STR -FORCE False
</pre>

<h2>salmon help</h2>

<pre class="code">
Prints out help for the commands.

salmon help

You can get help for one command with:

salmon help -for STR
</pre>

<h2>salmon log</h2>

<pre class="code">
Runs a logging only server on the given hosts and port.  It logs
each message it receives and also stores it to the run/queue
so that you can make sure it was received in testing.

salmon log -port 8825 -host 127.0.0.1 \
        -pid ./run/log.pid -chroot False  \
        -chdir "." -umask False -uid False -gid False \
        -FORCE False

If you specify a uid/gid then this means you want to first change to
root, set everything up, and then drop to that UID/GID combination.
This is typically so you can bind to port 25 and then become "safe"
to continue operating as a non-root user.

If you give one or the other, this it will just change to that
uid or gid without doing the priv drop operation.
</pre>

<h2>salmon queue</h2>

<pre class="code">
Let's you do most of the operations available to a queue.

salmon queue (-pop | -get | -remove | -count | -clear | -keys) -name run/queue
</pre>

<h2>salmon restart</h2>

<pre class="code">
Simply attempts a stop and then a start command.  All options for both
apply to restart.  See stop and start for options available.
</pre>

<h2>salmon routes</h2>

<pre class="code">
Prints out valuable information about an application's routing configuration
after everything is loaded and ready to go.  Helps debug problems with
messages not getting to your handlers.  Path has the search paths you want
separated by a ':' character, and it's added to the sys.path.

salmon routes -path $PWD -- config.testing -test ""

It defaults to running your config.testing to load the routes.
If you want it to run the config.boot then give that instead:

salmon routes -- config.boot

You can also test a potential target by doing -test EMAIL.
</pre>

<h2>salmon send</h2>

<pre class="code">
Sends an email to someone as a test message.
See the sendmail command for a sendmail replacement.

salmon send -port 8825 -host 127.0.0.1 -debug 1 \
        -sender EMAIL -to EMAIL -subject STR -body STR -attach False'
</pre>

<h2>salmon sendmail</h2>

<pre class="code">
Used as a testing sendmail replacement for use in programs
like mutt as an MTA.  It reads the email to send on the stdin
and then delivers it based on the port and host settings.

salmon sendmail -port 8825 -host 127.0.0.1 -debug 0 -- [recipients]
</pre>

<h2>salmon start</h2>

<pre class="code">
Runs a salmon server out of the current directory:

salmon start -pid ./run/smtp.pid -FORCE False -chroot False -chdir "." \
        -umask False -uid False -gid False -boot config.boot
</pre>

<h2>salmon status</h2>

<pre class="code">
Prints out status information about salmon useful for finding out if it's
running and where.

salmon status -pid ./run/smtp.pid
</pre>

<h2>salmon stop</h2>

<pre class="code">
Stops a running salmon server.  Give -KILL True to have it
stopped violently.  The PID file is removed after the
signal is sent.  Give -ALL the name of a run directory and
it will stop all pid files it finds there.

salmon stop -pid ./run/smtp.pid -KILL False -ALL False
</pre>

<h2>salmon version</h2>

<pre class="code">
    Prints the version of Salmon, the reporitory revision, and the
    file it came from.
</pre>

<h2>salmon web</h2>

<pre class="code">
Starts a very simple files only web server for easy testing of applications
that need to make some HTML files as the result of their operation.
If you need more than this then use a real web server.

salmon web -basedir "." -port 8888 -host '127.0.0.1'

This command doesn't exit so you can view the logs it prints out.
</pre>


