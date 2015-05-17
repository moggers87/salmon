==========================
Frequently Asked Questions
==========================


What is Salmon?
-----------------

Salmon is a pure Python SMTP server designed to create robust and complex mail
applications in the style of modern web frameworks such as Django. Unlike
traditional SMTP servers like Postfix or Sendmail, Salmon has all the features
of a web application stack (ORM, templates, routing, handlers, state machines,
Python) without needing to configure alias files, run newaliases, or juggle
tons of tiny fragile processes. Salmon also plays well with other web
frameworks and Python libraries.

Salmon is a fork of Lamson. In the summer of 2012 (2012-07-13 to be exact),
Lamson was relicenced under a BSD variant that was revokable. The two clauses
that were of most concern::

    4. Contributors agree that any contributions are owned by the copyright
       holder and that contributors have absolutely no rights to their
       contributions.

    5. The copyright holder reserves the right to revoke this license on anyone
       who uses this copyrighted work at any time for any reason. I read that
       to mean that I could make a contribution but then have said work denied
       to me because Mr. Shaw didn't like the colour of my socks. So I went and
       found the latest version that was available under the GNU GPL version 3.


Where does the name "Salmon" come from?
---------------------------------------

Salmon is an anagram of Lamson, if you hadn't worked it out already.

"Lamson Tubes" is a colloquial name for Pneumatic Tubes which were used last
century to deliver mail, packages, and hazardous material to the corporate
world.  They are still in use today.


What kind of applications do you envision being built on top of Salmon?
-----------------------------------------------------------------------

Why, spam of course (like I could stop that). As well as spam fighters,
greylisters, "campaign management" applications, mail firewalls, mime strippers
(for those Exchange file shares), help desk support applications, games,
mailing lists ('cause everyone loves writing those), and even SMTP portions of
just about any web site.

A few examples of applications that are actually written using Salmon (with
source included in the `source releases </releases/>`_

* `OneShotBlog <http://oneshotblog.com/>`_
* `Librelist <http://librelist.com/>`_
* `MyInboxIsNotA.TV <http://myinboxisnota.tv/>`_

With many more to come.


How do I install salmon on a Debian or CentOS server?
-----------------------------------------------------

Debian and CentOS are notorious for being dinosaurs. Both distributions of
Linux suffer from the false rationale that older software is more stable and
secure.  The reality is that the stability or security of a piece of software
is not a function of its age, and in many cases the newer versions of software
will typically fix many stability and performance problems.  Despite this fact,
these two variants of Linux are notorious for back-porting patches from later
versions to older versions rather than just using the newer version.

In order to help people who need to run a modern piece of software on their
antiquated operating systems, I've written an extensive document on :doc:`how
to Deploy Salmon <deploying_salmon>` that tells you how to do it in a way that
should work reliably on most Unix platforms, even if they have an older version
of Python. g.


How do I report a BUG/Feature/Question in Salmon?
---------------------------------------------------

In the Github issue list: https://github.com/moggers87/salmon/issues


How can I get the code to Salmon?
-----------------------------------

Clone or download it from the github repository.

What are Salmon's current features?
-------------------------------------

Salmon is currently running a handful of sites and is almost ready for a 1.0
release. It has these high level features:

* Very good bounce detection and analysis.
* Spam blocking.
* Get an application going quickly with the "salmon gen" command.
* Full set of :doc:`self-documented commands <salmon_commands>` for managing
  and developing a salmon application.
* Sample applications for you to base your work on.
* Handle mail for arbitrary hosts and addresses using simple regex routing.
* Process requests including full access to Python's complete MIME email
  libraries.
* Absolutely awesome full conversion to Unicode including complete cleaning of
  incoming mail.
* Routing requests in a standard web application framework style based on
  addresses.
* Processing mail messages (requests) in either simple generic handlers, or in
  more complex and robust state machines.
* Use any Python database storage you want.
* Use of Jinja2 or Mako templates, with Jinja2 as the default.
* Craft and send plain text or HTML email including attachments, with a great
  HTML mail generation API that even "knits" in CleverCSS.
* Unit test helpers for having a conversation, checking spelling, etc.
* Defer processing to Maildir queues for offline handling of bigger tasks.
* Extensive logging and development tools for debugging your email
  applications.
* Mutt configurations to fake out mutt so that it talks to your server.
* 100% code coverage in the unit tests.


Isn't Postfix/Sendmail/Exim Faster?
-----------------------------------

That is a tough question to answer actually.  If all you need to do is receive
and deliver email then a well established traditional email server like Postfix
or Exim (please don't use Sendmail) is the way to go.  Hands down these servers
are the fastest and the best at this job.

However, if you need to actually do something smart with your email, like
manage many mailing lists or handle support requests, then these servers are
definitely slower.

The reason is they require that you configure them to take messages they've
already received and hand them to a separate process like a Perl, Python, or
Ruby script.  This separate process then has to parse the message *again*, do
its job without stepping on any other processes that might be running (that
means locks), and then send response messages back to the server for even more
SMTP parsing.

With the triple and sometimes quadruple MIME parsing, the heavy weight
processes, the difficult to manage locking, and the additional configuration
headaches, there's no way traditional mail servers beat Salmon in speed.

Salmon only processes a message once, maybe twice if you defer to a queue. Once
the message is parsed you get full access to Python immediately, without
spawning a separate process.  Even if you defer to a queue, the Salmon dequeue
server stays resident and processes the queue without forking.  You can even
run many dequeue servers on mulitple machines processing a shared Maildir if
you need the extra processing.

In the end, threads and function calls beats processes and pipes.


Why not use Sendmail's Milter?
------------------------------

Sendmail has a protocol named "Milter" that lets you write a mail processing
server that acts as a sort of "slave" to the sendmail process.  This protocol
is supported by at least Postfix as well, maybe other servers.

Feel free to go try Milter.  When you're done trying to figure out the protocol
from the dense C code, configure the m4 macros, find a decent milter protocol
library that doesn't involve installing sendmail, and debugging the final
setup, then you can come back and have it easy with Salmon.


Why does Salmon send messages to a relay host?
----------------------------------------------

Salmon doesn't have to deliver to a relay host, but it is a smarter more
practical use of the technology.

Salmon is written in Python and does actually run slower than the established
mail servers.  In addition, Salmon is hopefully doing something more than just
routing email around to people.  It is probably processing messages, crafting
replies, querying databases, hitting REST interfaces, and all the other things
you'd want to do with a modern application.  This takes time and resources and
are probably more valuable operations than just simple delivery.

For this reason, you want to use a dumb workhorse like Postfix to do your
actual delivery, and reserve the smart processing that has value for Salmon.


What about security?! Shouldn't Salmon be 20 processes?
--------------------------------------------------------

Have you ever asked why other mail servers are a bundle of a billion processes?
Why have one server receiving mail, another routing it, and another handing it
to users?

The answer is back in the 1970's most mail was delivered to Unix users in their
home directories or similar files that required special access rights to
modify.  Also in the 1970's special ports like 25 for SMTP required root
access, which in the tiny Internet of the time meant that the server could be
"trusted".  These two realities of the time meant that to receive and deliver
mail at least some part of the system had to run as root.  To keep things safe,
modern mail systems reduce the amount of time spent as the root user by
separating their functionality into different processes.

However, if you never have to deliver to a user, and all you ever do is process
mail and talk to other servers like RDBMS, then why do you need all this
privilege separation?  Sites run just fine with systems running as one or two
processes without the complexity of some illogical privilege separation getting
in their way.

To put this into perspective, imagine that you were writing a Django
application and you were required to have a separate process for the HTTP
layers, the view layer, the model layer, the HTTP responses, and the RDBMS
access layers?  Each one required a different user, a different configuration
file, and you needed another process just to keep them all sane.  All of this
just so that if someone hacks into your HTTP server as root they supposedly
can't cause any damage.

Yet, they are on your server as root after all.

In practice, you can run Salmon as a separate root process, and then use
another "dequeue server" to do the real processing, if you feel you need that
security.

But, consider delaying that decision until you absolutely need it, because the
security benefits aren't worth the development and deployment hassles.

How come nobody thought of this before?
---------------------------------------

I don't know why, since it did seem kind of simple.  There's at least one other
project written in Perl called `qpsmtpd <http://smtpd.develooper.com/>`_ that
does something similar, and there may be more.  If you know others feel free to
`contact me </contact.html>`_ and let me know.


Isn't [Insert Random Java Mail Server] actually the first mail "framework"?
---------------------------------------------------------------------------

I get this quite frequently when I make the claim that Salmon is the first
email framework, and it may be true that there was a framework out there before
Salmon.  The internet is a big place, so anything is possible.  However, I
looked really hard and I couldn't find a single *modern* mail framework.  All
that existed were servers I could use to build a framework.

You see, around 2003 or 2004 the concept of "framework" changed.  Before then
all you needed was a server with an extension API named so that it rhymed with
"Servlet".  As long as your server provided a way to drop a class into the
processing queue and let a programmer handle the request you could call that a
framework.

The usual end result for these *servers* is that you could use them to build a
framework if you wanted, but what you'd get is affectionately called a
"frankenstack".  You'd grab an ORM from here, a template system from there,
maybe a workflow engine, write a Maven or Ant script to manage it, and wire it
all together with some lame secret sauce code you think gives you a competitive
edge.

Then along came the modern frameworks like Django and Rails that included
everything you needed in a bundle that you could use right away.  They had ORM,
templating, routing, higher level request processing, email support, REST
support, and anything else you might need for the 80% of your application you
don't care about.

Some people prefer less of these defaults, some people more, but nearly
everyone who has to get a project done prefers more than just an extension API
so they can build their own framework.

Today if you try to claim `Apache James <http://james.apache.org/>`_ is a
framework you'd be wrong.  I could *build* a framework with it, but I could
just as easily build that same framework with Python, Ruby, sendmail and even
postfix.  James and friends are just servers, not frameworks.  In fact, my
experience with James and similar Java mail servers is they are much harder to
use than aliases+pipes in Postfix.

I now advocate that if your framework doesn't at least support data, views, and
high level logic as first class entities then it's just a server.  You don't
have to use ORM, any particular templating, or Finite State Machines like
Salmon does.  You don't even have to settle on only one way to do data, views,
and logic.

You *must* at least support data, views, and logic out of the box so your user
doesn't have to go shopping at "APIs-R-Us" just to use your gear.



