===========================
Getting Started With Salmon
===========================

Salmon is designed to work like modern web application frameworks like Django,
TurboGears, ASP.NET, Ruby on Rails, and whatever PHP is using these days.  At
every design decision Salmon tries to emulate terminology and features found in
these frameworks.  This Getting Started document will help you get through that
terminology, get you started running your first salmon application, and walk
you through the code you should read.

In total it should take you about 30 minutes to an hour to complete.  If you
just want to try Salmon, at least go through the 30 *second* introduction given
first.


The 30 Second Introduction
--------------------------

If you have Python git try this out::

    $ git clone git@github.com:moggers87/salmon.git
    $ cd salmon
    $ python setup.py install
    $ salmon gen -project mymailserver
    $ cd mymailserver
    $ salmon start
    $ salmon log
    $ nosetests
    $ salmon help -for send
    $ salmon send -sender me``mydomain.com -to test``test.com \
        -subject "My test." \
        -body "Hi there." -port 8823
    $ less logs/salmon.log
    $ mutt -F muttrc

You now have a working base Salmon setup ready for you to work on with the
following installed:

* Salmon and all dependencies (Jinja2, nosetests)
* Code for your project in mymailserver.  Look in app/handlers and
  config/settings.py.
* Two initial tests that verify your server is not an open relay and forwards
  mail in tests/handlers/open_relay_tests.py.
* A "logger" server running on port 8825 that dumps all of its mail into the
  run/queue maildir.
* A config script for mutt (muttrc) that you can use to inspect the run/queue
  *and* also send mail using Salmon's *send* command.

When you're in mutt during the above test run, try sending an email.  The
included muttrc is configured to use the run/queue as the mail queue, and to
use the ``salmon sendmail`` command to deliver the mail.  This tricks mutt into
interacting directly with your running Salmon server, so you can test the thing
with a real mail client and see how it will work without having to actually
deploy the server.

Finally, if you wanted to stop all of above you would do::

    $ salmon stop -ALL run

Which tells Salmon to stop all processes that have a .pid file in the ``run``
directory.

Important Terminology
---------------------

If you are an old SMTP guru and/or you've never written a web application with
a modern web framework, then some of the terminology used in Salmon may seem
confusing.  Other terms may just confuse you or scare you because they sound
complicated.  I tried my best to make the concepts used in Salmon
understandable and the code that implements them easy to read.  In fact, you
could probably read the code to Salmon in an evening and understand how
everything works.

Experience has taught me that nobody reads the code, even if it is small.
Therefore, here are the most important concepts you should know to get a grasp
of Salmon and how it works.

* MVC(Model View Controller) -- Model View Controller is a design methodology
  used in web application frameworks where the data (model), presentation
  (view), and logic (controller) layers of the application are strictly
  separated.
* FSM(Finite State Machine) -- Salmon uses the concept of a Finite State
  Machine to control how handlers execute.  Each time it runs it will perform
  an action based on what it is send *and* what it was doing last.  FSM in
  computer science class are overly complex, but in Salmon they are as easy to
  use as a ``return`` statement.
* Template -- Salmon generates the bodies of its messages using Templates,
  which are text files that have parts that get replaced with variables you
  pass in.  Templates are converted to their final form with a process called
  *rendering*.
* Relay -- The *relay* for a Salmon server is where Salmon delivers its
  messages.  Usually the Relay is a smart tougher server that's not as smart,
  but very good at delivering mail.  Salmon can also be run as a Relay for
  testing purposes.
* Receiver -- Salmon typically runs as the Receiver of email.  If you are
  familiar with a web application setup, then Salmon is the inverse.  Instead
  of Salmon runing "behind" an Apache or Nginx server, Salmon runs "in front"
  of an SMTP server like Postfix.  It listens on port 25, handles the mail it
  should, and forwards the rest to the Relay.  This makes Salmon much more of a
  Proxy or filter server.
* Queue -- Salmon can also do all of its processing off a queue.  In this setup
  you would have your normal mail server dump all mail to a maildir queue, and
  then tell Salmon to process messages out of there.  This can be combined with
  the usual Receiver+Relay configuration for processing messages that might
  take a long time.
* Maildir -- A standard created for the qmail project with stores mail in a
  directory such that you can access the mail atomically and store it on a
  shared disk without conflicts or locking.


Managing Your Server
--------------------

Your Salmon application is now running inside the Salmon Python server.  This
is a very simple server based on Python's
`smtpd <http://docs.python.org/library/smtpd.html>`_ and
`asyncore <http://docs.python.org/library/asyncore.html>`_ libraries.

bq. If you want to know more about how it operates, take a look at the
``salmon/server.py`` file in the source distribution.

You'll need to use a few Salmon commands to manage the server.  You already
experienced them in the 30 second introduction, and you can review :doc:`them
all <salmon_commands>` or see them by using the ``salmon help`` command.

Right now you have Salmon running on port 8823 and a "Salmon logger" running on
8825.  This means that your salmon server (port 8823) will forward its messages
to the logger (port 8825) thinking it's your real relay server.  The truth is
the logger just logs its messages to logs/logger.log and dumps it into
run/queue so you can inspect the results.

Before we learn how to manage them and what they do, open up the
``config/settings.py`` file and take a look:

<pre class="code prettyprint"> from app.model import table import logging

relay_config = {'host': 'localhost', 'port': 8825}

receiver_config = {'host': 'localhost', 'port': 8823}

database_config = {
    "metadata" : table.metadata, "url" : 'sqlite:///app/data/main.db',
    "log_level" : logging.DEBUG }

handlers = ['app.handlers.sample']

router_defaults = {'host': 'test\\.com'}

template_config = {'dir': 'app', 'module': 'templates'}
</pre>

Your file probably has some comments telling you what these do, but it's
important to understand how they work.

First, this file is just plain old Python variables.  It is loaded by one of
two other files in your config directory:  ``config/boot.py`` or
``config/testing.py``.  The ``config/boot.py`` file is started whenever you use
the ``salmon start`` command and its job is to read the ``config/settings.py``
and start all the services you need, then assign them as variables back to
``config.settings`` so your handlers can get at them.  The
``config/testing.py`` is almost the same, except it configures
``config.settings`` so that your unit tests can run without any problems.
Typically this means setting the spell checker and *not* starting the real
server.

bq.  Salmon can load any boot script you like, see :doc:`Deferred Processing To
Queues <deferred_processing_to_queues>` for an example of using this to make a
queue processor.

The important thing to understand about this setup (where a boot file reads
settings.py and then configures ``config.settings``) that it makes it easy for
you to change Salmon's operations or start additional services you need and
configure them.  For the most part you won't need to touch ``boot.py`` or
``testing.py`` until you need to add some new service, change the template
library you want to use, setup a different database ORM, etc.  Until then just
ignore it.

settings.py Variables
---------------------

The ``receiver_config`` variable is used by the _salmon start_ command to
figure out where to listen for incoming SMTP connections.  In a real
installation this would be port *25* on your external IP address.  It's where
the internet talks to your server.

The ``relay_config`` setting is used by Salmon to figure out where to forward
message replies (responses) for real delivery.  Normally this would be a "smart
host" running a more established server like `Postfix <http://www.postfix.org/>`_
or `Exim <http://www.exim.org/>`_ to do the grunt work of delivering to the final
recipients.

The ``handlers`` variable lists the modules (not files) of the handlers you
want to load. Simply put them here and they'll be loaded, even the
`salmon.handlers <http://salmonproject.org/docs/api/salmon.handlers-module.html>`_
modules will work here too.

The ``router_defaults`` are for the
`salmon.routing.Router <http://salmonproject.org/docs/api/salmon.routing>`_
.RoutingBase-class.html class and configure the default routing regular
expressions you plan on using.  Typically you'll at least configure the
``host`` regular expression since that is used in every route and shouldn't
change too often.

Finally, ``template_config`` contains the configuration values for the
templating system you'll be using.  Salmon supports either Mako or Jinja2, but
defaults to Jinja2.


Looking At config/boot.py
-------------------------

Programmers need to know how everything works before they trust it, so let's
look at the _config/boot.py_ file and see how these variables are used:

<pre class="code prettyprint"> from config import settings from salmon.routing
import Router from salmon.server import Relay, SMTPReceiver from salmon.utils
import configure_database from salmon import view import logging import
logging.config import jinja2

# configure logging to go to a log file
  logging.config.fileConfig("config/logging.conf")

# the relay host to actually send the final message to settings.relay =
  Relay(host=settings.relay_config['host'], port=settings.relay_config['port'],
  debug=1)

# where to listen for incoming messages settings.receiver =
  SMTPReceiver(settings.receiver_config['host'],
  settings.receiver_config['port'])

settings.database = configure_database(settings.database_config,
also_create=False)

Router.defaults(**settings.router_defaults)
Router.load(settings.handlers)
Router.RELOAD=True

view.LOADER = jinja2.Environment(
    loader=jinja2.PackageLoader(settings.template_config['dir'],
                                settings.template_config['module']))

</pre>

bq. Don't be afraid that you see this much Python, you normally wouldn't touch
this file unless it were to add your own services or to make a new version for
a different configuration. For the most part, you can just edit the
``config/settings.py`` and go.

First you'll see that ``config/boot.py`` sets up logging using the
``config/logging.conf`` file, which you can change to reconfigure how you want
logs to be created.

Then it starts assigning variables to the config.settings module that it has
imported at the top.  This is important because after ``config.boot`` runs your
salmon code and handlers will have access to all these services.  You can get
directly to the relay, receiver, database and anything else you need by simply
doing:

<pre class="code prettyprint"> from config import settings </pre>

After that ``config.boot`` sets up the ``settings.relay``,
``settings.receiver``, and ``settings.database``.  These three are used heavily
in your own Salmon code, so knowing how to change them if you need to helps you
later.

After this we configure the ``salmon.routing.Router`` to have your defaults,
load up your handlers, and turn on RELOAD.  Setting ``Router.RELOAD=True`` tell
the Router to reload all the handlers for each request.  Very handy when you
are doing development since you don't need to reload the server so often.

bq.  If you deploy to production, then you'll want to set this to False since
it's a performance hit.

Finally, the ``config.boot`` does the job os loading the template system you'll
use, in this case Jinja2.  Jinja2 and Mako use the same API so you can
configure Mako here as well, as long as the object assigned to view.LOADER has
the same API it will work.


Developing With Salmon
======================

Now that you've received a thorough introduction to how to manage Salmon, and
how it is configured, you can get into actually writing some code for it.

Before you begin, you should know that writing an application for a mail server
can be a pain.  The clients and servers that handle SMTP make a large number of
assumptions based on how the world was back in 1975.  Everything is on defined
ports with defined command line parameters and the concept of someone pointing
their mail client at a different server arbitrarily just doesn't exist. The
world of email is not like the web where you just take any old "client" and
point it at any old server and start messing with it.

Lucky for you, Salmon has solved most of these problems and provides you with a
bunch of handy development tools and tricks so you can work with your Salmon
server without having to kill yourself in configuration hell.

Using Mutt
----------

You probably don't have another SMTP server running, and even if you did, it'd
be a pain to configure it for development purposes.  You'd have to setup
aliases, new mail boxes, restart it all the time, and other annoyances.

For development, what we want is our own little private SMTP relay, and since
Salmon can also deliver mail, that is what we get with the command:

<pre class="code"> $ salmon log </pre>

This tells Salmon to run as a "logging server", which doesn't actually deliver
any mail.  With this one command you have a server running on 8825 that takes
every mail it receives and saves it to the ``run/queue`` Maildir and also logs
it to ``logs/logger.log``.  It also logs the full protocol chat to
``logs/salmon.err`` so you can inspect it.

bq. Salmon uses Maildir by default since it is the most reliable and fastest
mail queue format available.  It could also store mail messages to any queue
supported by Python's `mailbox <http://docs.python.org/library/mailbox.html>`_
library.  If you were adventurous you could also use a RDBMS, but that's just
silly.

You also have the file ``muttrc`` which is configured to trick mutt into
talking to *your* running Salmon server, and then read mail out of the
``run/queue`` maildir that is filled in by the ``salmon log`` server.  Let's
take a look:

<pre class="code"> set mbox_type=Maildir set folder="run/queue" set
mask="!^\\.[^.]" set mbox="run/queue" set record="+.Sent" set
postponed="+.Drafts" set spoolfile="run/queue" set sendmail="/usr/bin/env
salmon sendmail -port 8823 -host 127.0.0.1" </pre>

Notice that it's configured sendmail to be "sendmail -port 8823 -host
127.0.0.1" which is a special ``salmon sendmail`` command that knows how to
talk to salmon and read the arguments and input that mutt gives to deliver a
mail.

bq.  Why does Salmon need its own sendmail?  Because you actually have to
configure most mail server's configuration files to change their ports before
their *sendmail command* will use a different port.  Yes, the average sendmail
command line tool assumes that it is always talking to one and only one server
on one and only one port for ever and all eternity.  Without ``salmon
sendmail`` you wouldn't be able to send to an arbitrary server.

With this setup (``salmon start`` ; ``salmon log`` ; ``mutt -F muttrc``) you
can now use your mutt client as a test tool for working with your application.


Stopping Salmon
---------------

The PID(Process ID) files are stored in the ``run`` directory.  Here's a sample
session where I stop all the running servers:

<pre class="code"> $ ls -l run/*.pid -rw-r--r--  1 zedshaw  staff  5 May 16
16:41 run/log.pid -rw-r--r--  1 zedshaw  staff  5 May 16 16:41 run/smtp.pid

$ salmon stop -ALL run Stopping processes with the following PID files:
['run/log.pid', 'run/smtp.pid'] Attempting to stop salmon at pid 1693
Attempting to stop salmon at pid 1689 </pre>

You can also pass other options to the stop command to just stop one server.
Use _salmon help -for stop_ to see all the options.

Starting Salmon Again
---------------------

Hopefully you've been paying attention and have figured out how to restart
salmon and the logging server.  Just in case, here it is again:

<pre class="code"> $ salmon start $ salmon log </pre>

You should also look in the logs/salmon.log file to see that it actually
started.  The other files in the logs directory contain messages dumped to
various output methods (like Python's stdout and stderr).  Periodically, if the
information you want is not in logs/salmon.log then it is probably in the other
files.

bq.  You can change your logging configuration by editing the logging line your
config/settings.py file.


Other Useful Commands
---------------------

You should read the :doc:`available commands <salmon_commands>` documentation
to get an overview, and you can also use _salmon help_ to see them at any time.

send
----

The first useful command is _salmon send_, which lets you send mail to SMTP
servers (not just Salmon) and watch the full SMTP protocol chatter.  Here's a
sample:

<pre class="code"> $ salmon send -port 25 -host zedshaw.com -debug 1 \ -sender
tester``test.com -to zedshaw``zedshaw.com \ -subject "Hi there" -body "Test
body."
send: 'ehlo zedshawscomputer.local\r\n'
reply: '502 Error: command "EHLO" not implemented\r\n'
reply: retcode (502); Msg: Error: command "EHLO" not implemented
send: 'helo zedshawcomputer.local\r\n'
reply: '250 localhost.localdomain\r\n'
reply: retcode (250); Msg: localhost.localdomain
send: 'mail FROM:<tester@test.com>\r\n'
reply: '250 Ok\r\n'
reply: retcode (250); Msg: Ok
send: 'rcpt TO:<zedshaw@zedshaw.com>\r\n'
reply: '250 Ok\r\n'
reply: retcode (250); Msg: Ok
send: 'data\r\n'
reply: '354 End data with <CR><LF>.<CR><LF>\r\n'
reply: retcode (354); Msg: End data with <CR><LF>.<CR><LF>
data: (354, 'End data with <CR><LF>.<CR><LF>')
send: 'Content-Type: text/plain; charset="us-ascii"\r\nMIME-Version: 1.0\r\nContent-Transfer-Encoding: 7bit\r\nSubject: Hi there\r\nFrom: tester``test.com\r\nTo: zedshaw``zedshaw.com\r\n\r\n.\r\n'
reply: '250 Ok\r\n'
reply: retcode (250); Msg: Ok
data: (250, 'Ok')
send: 'quit\r\n'
reply: '221 Bye\r\n'
reply: retcode (221); Msg: Bye
</pre>

Using this helps you debug your Salmon server by showing you the exact protocol
sent between you and the server.  It is also a useful SMTP server debug command
by itself.

bq.  When you use the supplied muttrc you'll be configured to use Salmon's
sendmail (not *send) command as your delivery command.  This lets you use mutt
as a complete development tool with minimal configuration.

queue
-----

The _salmon queue_ command lets you investigate and manipulate the run/queue
(or any maildir). You can pop a message off, get a message by its key, remove a
message by its key, count the messages,clear the queue, list keys in the queue.
It gives you a lower level view of the queue than mutt would, and lets you
manipulate it behind the scenes.

restart
-------

Salmon does reload the code of your project when it receives a new request
(probably too frequently), but if you change the ``config/settings.py`` file
then you need to restart. Easiest way to do that is with the restart command.

Walking Through The Code
------------------------

You should actually know quite a lot about how to run and mess with Salmon, so
you'll want to start writing code.  Before you do, go check out the "API
Documentation":/docs/api/ and take a look around.  This document will guide you
through where everything is and how to write your first handler, but when you
start going out on your own you'll need a good set of reference material.

At the top level of your newly minted project you have these directories:

<pre class="code"> app -- Where the application code (handlers, templates,
models) lives. config -- You already saw everything in here. logs -- Log files
get put here. run -- Stuff that would go in a /var/run like PID files and
queues. tests -- Unit tests for handlers, templates, and models. </pre>

Salmon expects all of these directories to be right there, so don't get fancy
and think you can move them around.

The first place to look is in the app directory, which has this:

<pre class="code"> app/__init__.py app/data -- Data you want to keep around
goes here. app/handlers -- Salmon handlers go here. app/model -- Any type of
backend ORM models or other non-handler code. app/templates -- Email templates.
</pre>

You don't technically *have* to store your data in app/data.  You are free to
put it anywhere you want, it's just convenient for most situations to have it
there.

Your ``app/model`` directory could have anything in it from simple modules for
working various Maildir queues, to full blown SQLAlchemy configurations for
your database.  The only restriction is that you load them in the modules
yourself (no magic here).

The ``app/templates`` directory can have any structure you want, and as you saw
from the ``config.boot`` discussion it is just configured into the Jinja2
configuration as the default.  If you have a lot of templates it might help to
have them match your ``app/handlers`` layout in some logical way.

That only leaves your ``app/handlers`` directory:

<pre class="code"> app/handlers/__init__.py app/handlers/sample.py </pre>

This is where the world gets started.  If you look at your ``config.settings``
you'll see this line:

<pre class="code prettyprint"> handlers = ['app.handlers.sample'] </pre>

Yep, that's telling the
`salmon.routing.Router <http://salmonproject.org/docs/api/salmon.routing>`_
.RoutingBase-class.html to load your ``app.handlers.sample`` module to kick it
into gear.  It really is as simple as just putting the file in that directory
(in in sub-modules there) and then adding them to the handlers list.

You can also add handlers from modules outside of your ``app.handlers``:

<pre class="code prettyprint"> handlers = ['app.handlers.sample',
'salmon.handlers.log'] </pre>

This installs the handler
(`salmon.handlers.log <http://salmonproject.org/docs/api/salmon.handlers.log->`_
module.html) that salmon uses to log every email it receives.

Writing Your Handler
--------------------

This document is for getting started quickly, so going into the depths of the
cool stuff you can do with Salmon handlers is outside the scope, but if you
open the _app/handlers/sample.py_ file and take a look you'll how a handler is
structured.

bq. Since Salmon is changing so much the contents of the file aren't included
in this document.  You'll have to open it and take a look.

At the top of the file you should see your typical import statements:

<pre class="code prettyprint"> import logging from salmon.routing import route,
route_like, stateless from config.settings import relay, database from salmon
import view </pre>

Notice that we include elements from the ``salmon.routing`` that are decorators
we use to configure a route.  Then you'll see that we're getting that
``settings.relay`` and ``settings.database`` we configured in the previous
sections.  Finally we bring in the ``salmon.view`` module directory to make
rendering templates into email messages a lot easier.

Now take a look at the rest of the file and you'll how a handler is structured:

# Each state is a separate function in CAPS.  It doesn't have to be, it just
  looks better.
# Above each state function is a
  `route <http://salmonproject.org/docs/api/salmon.routing.route-class.html,>`_
  `route_like <http://salmonproject.org/docs/api/salmon.routing.route_like->`_
  class.html, or `stateless <http://salmonproject.org/docs/api/salmon.routing->`_
  module.html#stateless decorator to configure how ``salmon.routing.Router``
  uses it.
# The `route <http://salmonproject.org/docs/api/salmon.routing.route-class.html>`_
  decorator takes a pattern and then regex keyword arguments to fill it in.
  The words in the pattern string are replaced in the final more complex
  routing regex by the keyword arguments after.  However, *if you want to use
  regex directly you can*,
  `route <http://salmonproject.org/docs/api/salmon.routing.route-class.html>`_
  just needs a string that eventually becomes a regex.
# A state function changes state by returning the next function to call.  You
  want to go to the RUNNING state, just ``return RUNNING``.
# If any state function throws an error it will go into the ``ERROR`` state, so
  if you make a state handler named ERROR it will get called on the next event
  and can recover.
# If you want to run a state on this event rather than wait to have it run on
  the next, then simple call it and return what it returns.  So to have RUNNING
  go now, just do @return RUNNING(message, ...)@ and it will work.
# If a state has the same regex as another state, just use
  `route_like <http://salmonproject.org/docs/api/salmon.routing.route_like->`_
  class.html to say that.
# If you have a `stateless <http://salmonproject.org/docs/api/salmon.routing->`_
  module.html#stateless decorator after a
  `route <http://salmonproject.org/docs/api/salmon.routing.route-class.html>`_ or
  `route_like <http://salmonproject.org/docs/api/salmon.routing.route_like->`_
  class.html, then that handler will run for *all* addresses that match, not
  just if this handler is in that state.

That is pretty much the entire complexity of how you write a handler.  You
setup routes, and return the next step in your conversation as the next
function to run.   The ``salmon.routing.Router`` then takes each message it
receives and runs it through a processing loop handing it to your states and
handlers.

How States Are Run
------------------

The best way to see how states are processed is to look at the
`Router <http://salmonproject.org/docs/api/salmon.routing.RoutingBase->`_
class.html code that does it:

<pre class="code prettyprint"> def deliver(self, message): if self.RELOAD:
    self.reload()

        called_count = 0

        for functions, matchkw in self.match(message['to']): to_call = []
            in_state_found = False

            for func in functions: if salmon_setting(func, 'stateless'):
                to_call.append(func) elif not in_state_found and
                self.in_state(func, message): to_call.append(func)
                in_state_found = True

            called_count += len(to_call)

            for func in to_call: if salmon_setting(func, 'nolocking'):
                self.call_safely(func, message,  matchkw) else: with
                self.call_lock: self.call_safely(func, message, matchkw)

        if called_count == 0: if self.UNDELIVERABLE_QUEUE: LOG.debug("Message
            to %r from %r undeliverable, putting in undeliverable queue.",
            message['to'], message['from'])
            self.UNDELIVERABLE_QUEUE.push(message) else: LOG.debug("Message to
            %r from %r didn't match any handlers.", message['to'],
            message['from']) </pre>

What this does is take all the handlers you've loaded, and then finds which
handlers have a state function that matches the current message.  It then goes
through each potential match, and determines which of all the matching state
functions is "in that state".  This means that, even though you have six state
functions that answer to "(list_name)-(action)@(host)" only the one that
matches the users current state (say PENDING) will be called next. As it goes
through these functions it also loads up any that are marked "stateless" so
they can be called as well.

Finally, it just calls them in order.  If the message results in no methods to
call, then it will take the message and tell you this, or put it into an
``UNDELIVERABLE_QUEUE`` for you to review it later.

bq.  Slight design criticism:  Currently the order of these calls is fairly
deterministic, but you can't rely on it. It's also not clear if *all* matching
states should run, or just the first.  It currently only runs the first match,
but it might be better to run each match from each handler.  Suggestions
welcome on this.


Debugging Routes
----------------

In the old way of doing routing you would edit a large table of "routes" in
your ``config/settings.py`` file and then that told Salmon how to run.  The
problem with this is it was too hard to maintain and too hard to indicate that
different states needed a different route.

The new setup is great because all your routing for each handler module is
right there, and it's easy to see what will cause a particular state function
to go off.

What sucks about the new setup is that you can't find out what all the routes
are doing *globally* in one place.  That's where ``salmon routes`` comes in.
Simply run that command and you'll get a debug dump of all the full routing
regex and the functions and modules they belong to:

<pre class="code"> Routing ORDER:
['^(?P&lt;address>.+)@(?P&lt;host>test\\.com)$'] Routing TABLE:
---
'^(?P&lt;address>.+)@(?P&lt;host>test\\.com)$':  app.handlers.sample.START  app.handlers.sample.NEW_USER
   app.handlers.sample.END  app.handlers.sample.FORWARD
---
</pre>

This is telling you which regex is matched first, then what those regex are
mapped to.  This is very handy as you can copy-paste that regex right into a
python shell and then play with it to see if it would match what you want.

You can also pass in an email address to the ``-test`` option and it will tell
you what routes would match and which functions that will call:

<pre class="code"> osb $ salmon routes -test test.blog@oneshotblog.com
2009-06-07 02:33:31,678 - root - INFO - Database configured to use
sqlite:///app/data/main.db URL. Routing ORDER:  [... lots of regex here ...]
Routing TABLE:
---
... each regex and what state functions it maps ..
---
'^post-confirm-(?P<id_number>[a-z0-9]+)@(?P<host>oneshotblog\\.com)$':
app.handlers.post.CONFIRMING
---

TEST address 'test.blog@oneshotblog.com' matches:
  '^(?P<post_name>[a-zA-Z0-9][a-zA-Z0-9.]+)@(?P<host>oneshotblog\\.com)$'
  app.handlers.index.POSTING
  -  {'host': 'oneshotblog.com', 'post_name': 'test.blog'}
     '^(?P<post_name>[a-zA-Z0-9][a-zA-Z0-9.]+)@(?P<host>oneshotblog\\.com)$'
     app.handlers.post.START
  -  {'host': 'oneshotblog.com', 'post_name': 'test.blog'}
     '^(?P<post_name>[a-zA-Z0-9][a-zA-Z0-9.]+)@(?P<host>oneshotblog\\.com)$'
     app.handlers.post.POSTING
  -  {'host': 'oneshotblog.com', 'post_name': 'test.blog'}
osb $
</pre>

If you're working with Salmon this is incredibly helpful, because it tells you
what routes you have, what functions they call, and then it'll take an email
address and tell you all the routes that match it.


THREADING!
----------

Salmon takes a lighter approach to how it runs.  It assumes that most of the
time you want salmon to keep itself sane with minimal locking, and that you
want each of your state functions to run in a thread lock that prevents others
from stepping on your operations.  In 95% of the cases, this is what you want.

To accomplish this, Salmon's router will acquire an internal lock for
operations that change its state, and a separate lock before it calls each
state function.  Since multiple state functions run inside each thread, but one
thread handles each message, you'll get multiple processing, but each state
won't step on other states in the system.

However, it's those 5% of the times that will kill your application, and if you
know what you're doing, you should be able to turn this off.  In order to tell
the Router *not* to lock your state function, simply decorate it with
`nolocking <http://salmonproject.org/docs/api/salmon.routing->`_
module.html#nolocking and Salmon will skip the locking and just run your state
raw.  This means that other threads will run potentially stepping on your
execution, so you *must* do your own locking.

Now, don't think that slapping a
`nolocking <http://salmonproject.org/docs/api/salmon.routing-module.html#nolocking>`_
on your state functions is some magic cure for performance issues.  You only
ever want to do this if you *really* know your stuff, and you know how to make
that operation faster with better controlled locking.

The reality is, if you have an operation that takes so long it blocks
everything else, then you are doing it wrong by trying to do it all in your
state function.  You should change your design so that this handler drops the
message into a
`salmon.queue.Queue <http://salmonproject.org/docs/api/salmon.queue.Queue->`_
class.html and that *another* Salmon server reads messages out of that to do
the long running processing.

Using queues and separate Salmon servers you can solve most of your processing
issues without a lot of thread juggling and process locking.  In fact, since
Salmon uses maildir queues by default you can even spread these processors out
to multiple machines reading off a shared disk and everything will be just
fine.

But, since programmers will always want to just try turning off the locking,
Salmon supports the ``nolocking`` decorator.  Use with care.


What's In A Unit Test
---------------------

Writing unit tests is way outside the scope of this document, but you should
read up on using nosetests, testunit, and you should look at
`salmon.testing <http://salmonproject.org/docs/api/salmon.testing-module.html>`_
for a bunch of helper functions.  Also look in the generated ``tests``
directory to see some examples.

Spell Checking Your Email Templates
-----------------------------------

Another big help is that Salmon has support for
`PyEnchant <http://www.rfk.id.au/software/pyenchant/>`_ so you can spell check
your templates.  You can use
`salmon.testing.spelling <http://salmonproject.org/docs/api/salmon.testing->`_
module.html#spelling function in your unit tests.

Installing PyEnchant is kind of a pain, but the trick is to get the dictionary
you want and put it in your ``~/.enchant/myspell`` directory.  You'll also want
to open the ``config/testing.py`` file and uncomment the lines at the bottom
that tell PyEnchant where to find the enchant so (dylib).

PyEnchant is kind of hard to use, so if you have suggestions on a better Python
spell checking lib for unit tests please let `me know. </contact.html>`_


Spam Filtering For Free
-----------------------

Salmon comes with the
`salmon.spam <http://salmonproject.org/docs/api/salmon.spam-module.html>`_ module
which supports `SpamBayes <http://spambayes.sourceforge.net/>`_ spam filtering
system.

Read the document on :doc:`Filtering Spam With Salmon <filtering_spam>` to get
a full set of instructions on using the spam filtering features.


Other Examples
--------------

Next you'll want to sink your teeth in a bigger example.  Go grab "the source
distribution .tar.gz":/releases/ and extract it so you can get at the examples:

<pre class="code"> $ tar -xzvf salmon-VERSION.tar.gz $ cd salmon-VERSION $ cd
examples/osb </pre>

You are now in the osb example that is running on
`oneshotblog.com <http://oneshotblog.com/.>`_  Using what you've learned so far
you can start reviewing the code and finding out how a working example
operates.

Getting Help
------------

As you work through this documentation, send your questions "to
me":/contact.html and I'll try to help you.  You can also join the
`salmon``librelist.com mailing list <mailto:salmon``librelist.com>`_ and get help
from other Salmon users.

