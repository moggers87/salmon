==========================
 Deploying Salmon Level 1
==========================

These instructions will teach you how to setup a completely clean Python 2.6
installation, a virtualenv with salmon, and all the gear needed to run the
`oneshotblog.com <http://oneshotblog.com/>`_ software on your machine.

You can then :doc:`read how to install oneshotblog <deploying_oneshotblog>`
for yourself.

Most of these instructions could be easily turned into an automated script,
which may happen in the future.  For now it is meant to teach you about the
typically dirty details involved in setting up a system for the first time.  It
also tries to avoid various problems with different operating systems, so let
me know how it works for you.

A Warning
---------

Deploying server software is a notoriously nasty process, especially the first
10 or 20 times.  Most operating systems do their best to enforce completely
arbitrary restrictions on your file layouts and configurations, and every
system has different arbitrary restrictions.

When you go through these instructions, make sure you stay awake and be ready
to delve into why a particular step might not work on your system.  There's a
good chance you missed something or that there's something just slightly
different about your system that makes the step not work.

For example, in the parts of this document where I setup
`oneshotblog.com <http://oneshotblog.com/>`_ I ran into a problem with
`SpamBayes <http://spambayes.sourceforge.net/>`_ dying because it couldn't iterate
a bsddb.  Problem is this works just fine in the exact same setup on a CentOS
machine and was only dying on a MacOSX machine that I later tested.  For
whatever reason, the exact same setup can't run SpamBayes on OSX, even though
it can run with the stock Python 2.5 in OSX.

To solve the problem I just had to show you how to disable SpamBayes in the
oneshotblog.com code so you could test it.  That's just how deployment goes.
You get on a machine and start setting things up and then 2/3 of the way
through the configuration you find out that something doesn't work.

Only choices are to work around the problem (like I did) or try to figure out
why your machine is different and fix it.


Step 0: Setup A Workplace
-------------------------

You'll want a directory to do this in so that you don't screw up your machine.
Here's what I did:

<pre class="code">
$ mkdir deploy
$ cd deploy
$ export DEPLOY=$PWD
</pre>

That last bit is so you can refer to this deployment directory with $DEPLOY
(which I'll be using in the instructions from now on).


Step 1: Get Python
------------------

Many operating systems have old versions of Python, and even though Salmon
works with 2.6 or 2.5, you'll probably want to get 2.6 for your deployment.  If
your OS has 2.6 available then go ahead and install it.

If it doesn't have the right Python version, then here's how you can install it
from source and use it as your default Python.  To do this, just punch in these
commands:

<pre class="code">
$ mkdir source
$ cd source
$ wget http://www.python.org/ftp/python/2.6.2/Python-2.6.2.tgz
$ tar -xvf Python-2.6.2.tgz
$ cd Python-2.6.2
$ ./configure --prefix=$DEPLOY
$ make
$ make install
</pre>

After this you will have a bunch of new directories in $DEPLOY:

<pre class="code">
$ ls $DEPLOY
bin     include lib     share   source
</pre>

Finally, you just have to put this new bin directory into your $PATH:

<pre class="code">
$ export PATH=$DEPLOY/bin:$PATH
</pre>

... then you just try it out to make sure that you have the right one:

<pre class="code">
Python-2.6.2 $ which python
$DEPLOY/deploy/bin/python

Python-2.6.2 $ python
Python 2.6.2 (r262:71600, Jun  8 2009, 00:44:56)
[GCC 4.0.1 (Apple Inc. build 5490)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>> ^D
</pre>

That's it, you'll now be able to use this Python when you need to run your
Salmon server, and setup a virtualenv (coming next) so that you're walled off
from the rest of the system.

bq.  Operating system fanatics will scoff at putting the python install in this
directory, so if you want you can just install it to the default /usr/local on
your system and deal with all the various clashes and conflicts you'll have,
especially if you are on an MacOSX machine.

Step 2: Install VirtualEnv
--------------------------

Now we need to create a "virtual environment" to install all your software.  To
do this we'll need easy_install installed to your $DEPLOY directory:

<pre class="code">
$ cd $DEPLOY/source
$ wget http://peak.telecommunity.com/dist/ez_setup.py
$ python ez_setup.py
$ which easy_install
$DEPLOY/bin/easy_install
</pre>

As you can see, you now have a clean install of easy_install in your fresh
$DEPLOY/bin directory for you to use.  Now you need to install ``virtualenv``:

<pre class="code">
$ easy_install --prefix $DEPLOY virtualenv
$ which virtualenv
$DEPLOY/bin/virtualenv
</pre>

bq. Make sure you use ``--prefix $DEPLOY`` above or you'll install things into
the default system setup even though easy_install is clearly and obviously
running from a Python in a totally different location so easy_install should
know that.


Step 3: Create Your VirtualEnv
------------------------------

With that you are ready to setup your virtual environment which will house your
Salmon setup and fill it with the gear you need.

First up is getting your virtualenv created and activated:

<pre class="code">
$ cd $DEPLOY
$ virtualenv LAMSON
New python executable in LAMSON/bin/python
Installing setuptools............done.
$ cd LAMSON
$ . bin/activate
</pre>

That's pretty simple, and it tells you clearly that you are using the LAMSON
virtualenv.  It prepends that to your currently prompt, so your prompt may look
different.

After that we can use easy_install to install our packages to this LAMSON
virtual env.  Keep in mind that these packages will be in $DEPLOY/LAMSON, so
they won't infect your regular $DEPLOY setup.

<pre class="code">
$ cd $DEPLOY/LAMSON
$ easy_install salmon
</pre>

After that, you have salmon installed and ready to go, and you can install
anything you want, but there is one catch:

bq. You *MUST* be in the $DEPLOY/LAMSON directory or easy_install barfs
complaining that the package is not there.

Step 4: Making Sure It Works
----------------------------

All of this setup is pointless if you can't get back to it later, so exit your
terminal completely and start a new one so you can do this:

<pre class="code">
$ cd projects/salmon/deploy/
$ export DEPLOY=$PWD
$ export PATH=$DEPLOY/bin:$PATH
$ cd $DEPLOY/LAMSON
$ . bin/activate
(LAMSON) $ which python
$DEPLOY/deploy/LAMSON/bin/python
(LAMSON) $ which easy_install
$DEPLOY/deploy/LAMSON/bin/easy_install
(LAMSON) $ which salmon
$DEPLOY/deploy/LAMSON/bin/salmon
(LAMSON) $ cd $DEPLOY
(LAMSON) $ salmon help
</pre>

If you can do all that, then you know you've got the setup going, now you just
need a little shell script to kick this all into gear automatically:

<pre class="code prettyprint">
#!/bin/sh

export DEPLOY=$PWD
export PATH=$DEPLOY/bin:$PATH
cd $1
source bin/activate
cd $DEPLOY
</pre>

To use this script, you just do this:

<pre class="code">
$ cd projects/salmon/deploy
$ . activate LAMSON
</pre>

With that you have a fully ready to go setup that's not using your normal
system's Python at all, has Python 2.6 installed, a fully virtualenv, and the
start of your salmon setup.


Conclusion
----------

Your next step is to try and setup `oneshotblog <http://oneshotblog.com/>`_ using
the :doc:`instructions I've written <deploying_oneshotblog>` to follow
these instructions.

This document is very fresh, so send me feedback on your experience with
running through it.  Make sure you tell me what system you are on and that you
ran each command exactly when you do.


