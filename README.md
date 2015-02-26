The Salmon Mail Server

======================

Salmon is a pure Python SMTP server designed to create robust and complex mail
applications in the style of modern web frameworks such as Django. Unlike
traditional SMTP servers like Postfix or Sendmail, Salmon has all the features
of a web application stack (ORM, templates, routing, handlers, state machines,
Python) without needing to configure alias files, run newaliases, or juggle
tons of tiny fragile processes. Salmon also plays well with other web
frameworks and Python libraries.

Features
========

Salmon supports running in many contexts for processing mail using the best
technology currently available.  Since Salmon is aiming to be a modern SMTP
server and Mail processing framework, it has some features you don't find in any
other Mail server.

* Written in portable Python that should run on almost any Unix server.
* Handles mail in almost any encoding and format, including attachments, and
canonicalizes them for easier processing.
* Sends nearly pristine clean mail that is easier to process by other receiving
servers.
* Properly decodes internationalized mail into Python unicode, and translates
Python unicode back into nice clean ascii and/or UTF-8 mail.
* Salmon can use SQLAlchemy, TokyoCabinet, or any other database abstraction
layer or technology you can get libraries for.  It supports SQLAlchemy by
default.
* It uses Jinja2 by default, but you can swap in Mako if you like, or any other
template framework with a similar API.
* Supports working with Maildir queues to defer work and distribute it to
multiple machines.
* Can run as an non-root user on port 25 to reduce the risk of intrusion.
* Salmon can also run in a completely separate virtualenv for easy deployment.
* Spam filtering is baked into Salmon using the SpamBayes library.
* A flexible and easy to use routing system lets you write stateful or stateLESS
handlers of your email.
* Helpful tools for unit testing your email applications with nose, including
spell checking with PyEnchant.
* Ability to use Jinja2 or Mako templates to craft emails including the headers.
* A full alternative to the default optparse library for doing commands easily.
* Easily configurable to use alternative sending and receiving systems, database
libraries, or any other systems you need to talk to.
* Yet, you don't *have* to configure everything to get stated.  A simple
salmon gen command lets you get an application up and running quick.
* Finally, many helpful commands for general SMTP server debugging and cleaning.


Installing
==========

There's a setup.py

Project Information
===================

More documentation is forthcoming, but you probably want to know how to at least 
try out your installation.  This presumes that you have already installed a 
fairly recent copy of python and that you have grabbed the source using
git clone.  If you don't know how to do those things, there is documentation 
on the web that you can use to get python and git installed.  Do that first then
come back here.

So to begin with once you download the source you will need to change directory
to the root of the project folder in this documentation we will refer to that path
using the following tag ${salmon-dir}.  Also as a convention we will prefix
command line statements with '#: '.  When you see '#: ' at the beginning of an example
it indicates a command you type in.  Other output in the example will be devoid of the
'#: ' prefix, indicating machine output.

```
#: cd ${salmon-dir}
```

Next you will want to run the python install on salmon.

```
#: sudo python setup.py install
```

After you have installed salmon you can use the salmon command to probe the system further.
For example:

```
#: $ salmon sowens$ salmon 
Available commands:

blast, cleanse, gen, help, log, queue, restart, routes, send, sendmail, start, status, stop, version, web

Use salmon help -for <command> to find out more.
```
To start the system use 

```
#: salmon start
Traceback (most recent call last):
  File "/usr/local/bin/salmon", line 5, in <module>
    pkg_resources.run_script('salmon-mail==2', 'salmon')
  File "/System/Library/Frameworks/Python.framework/Versions/2.7/Extras/lib/python/pkg_resources.py", line 489, in run_script
    self.require(requires)[0].run_script(script_name, ns)
  File "/System/Library/Frameworks/Python.framework/Versions/2.7/Extras/lib/python/pkg_resources.py", line 1207, in run_script
    execfile(script_filename, namespace, namespace)
  File "/Library/Python/2.7/site-packages/salmon_mail-2-py2.7.egg/EGG-INFO/scripts/salmon", line 7, in <module>
    args.parse_and_run_command(sys.argv[1:], commands, default_command="help")
  File "build/bdist.macosx-10.7-intel/egg/modargs/args.py", line 381, in parse_and_run_command
  File "build/bdist.macosx-10.7-intel/egg/modargs/args.py", line 286, in command_module
  File "/Library/Python/2.7/site-packages/salmon_mail-2-py2.7.egg/salmon/commands.py", line 122, in start_command
    utils.start_server(pid, FORCE, chroot, chdir, uid, gid, umask, loader, debug, daemon)
  File "/Library/Python/2.7/site-packages/salmon_mail-2-py2.7.egg/salmon/utils.py", line 107, in start_server
    daemonize(pid, chdir, chroot, umask, files_preserve=[])
  File "/Library/Python/2.7/site-packages/salmon_mail-2-py2.7.egg/salmon/utils.py", line 45, in daemonize
    context.stdout = open(os.path.join(chdir, "logs/salmon.out"),"a+")                                                                                                       
IOError: [Errno 2] No such file or directory: './logs/salmon.out'
```

Notice that it doesn't work yet.  Salmon doesn't create the logs directory by default nor does it have a
default home directory.  When you invoke salmon start, it is expecting a writable directory in whatever 
folder you happen to be in at the time you invoke the command.

So let's make a log directory and run salmon again.  Perhaps it will work now:

```
#: mkdir logs
#: salmon start
#: ps -efwww | grep salmon
1020816403 25463 67429   0 10:07AM ttys003    0:00.00 grep salmon
$: ls logs
salmon.err	salmon.out
#:salmon sowens$ vi logs/salmon.err
```
Unfortunately not quite yet.  But at least we know where to look to find out what went wrong.  
The last command above looks at the log file and we can see:

```
Traceback (most recent call last):
  File "/usr/local/bin/salmon", line 5, in <module>
    pkg_resources.run_script('salmon-mail==2', 'salmon')
  File "/System/Library/Frameworks/Python.framework/Versions/2.7/Extras/lib/python/pkg_resources.py", line 489, in run_script
    self.require(requires)[0].run_script(script_name, ns)
  File "/System/Library/Frameworks/Python.framework/Versions/2.7/Extras/lib/python/pkg_resources.py", line 1207, in run_script
    execfile(script_filename, namespace, namespace)
  File "/Library/Python/2.7/site-packages/salmon_mail-2-py2.7.egg/EGG-INFO/scripts/salmon", line 7, in <module>
    args.parse_and_run_command(sys.argv[1:], commands, default_command="help")
  File "build/bdist.macosx-10.7-intel/egg/modargs/args.py", line 381, in parse_and_run_command
  File "build/bdist.macosx-10.7-intel/egg/modargs/args.py", line 286, in command_module
  File "/Library/Python/2.7/site-packages/salmon_mail-2-py2.7.egg/salmon/commands.py", line 122, in start_command
    utils.start_server(pid, FORCE, chroot, chdir, uid, gid, umask, loader, debug, daemon)
  File "/Library/Python/2.7/site-packages/salmon_mail-2-py2.7.egg/salmon/utils.py", line 107, in start_server
    daemonize(pid, chdir, chroot, umask, files_preserve=[])
  File "/Library/Python/2.7/site-packages/salmon_mail-2-py2.7.egg/salmon/utils.py", line 56, in daemonize
    context.open()
  File "/Library/Python/2.7/site-packages/python_daemon-2.0.5-py2.7.egg/daemon/daemon.py", line 372, in open
    self.pidfile.__enter__()
  File "/Library/Python/2.7/site-packages/lockfile-0.10.2-py2.7.egg/lockfile/__init__.py", line 238, in __enter__
    self.acquire()
  File "/Library/Python/2.7/site-packages/lockfile-0.10.2-py2.7.egg/lockfile/pidlockfile.py", line 94, in acquire
    raise LockFailed("failed to create %s" % self.path)
lockfile.LockFailed: failed to create ./run/smtp.pid
```

Looks like we also need to create a run directory.

```
#: mkdir run
#: salmon start
#: cat logs/salmon.err
Traceback (most recent call last):
  File "/usr/local/bin/salmon", line 5, in <module>
    pkg_resources.run_script('salmon-mail==2', 'salmon')
  File "/System/Library/Frameworks/Python.framework/Versions/2.7/Extras/lib/python/pkg_resources.py", line 489, in run_script
    self.require(requires)[0].run_script(script_name, ns)
  File "/System/Library/Frameworks/Python.framework/Versions/2.7/Extras/lib/python/pkg_resources.py", line 1207, in run_script
    execfile(script_filename, namespace, namespace)
  File "/Library/Python/2.7/site-packages/salmon_mail-2-py2.7.egg/EGG-INFO/scripts/salmon", line 7, in <module>
    args.parse_and_run_command(sys.argv[1:], commands, default_command="help")
  File "build/bdist.macosx-10.7-intel/egg/modargs/args.py", line 381, in parse_and_run_command
  File "build/bdist.macosx-10.7-intel/egg/modargs/args.py", line 286, in command_module
  File "/Library/Python/2.7/site-packages/salmon_mail-2-py2.7.egg/salmon/commands.py", line 122, in start_command
    utils.start_server(pid, FORCE, chroot, chdir, uid, gid, umask, loader, debug, daemon)
  File "/Library/Python/2.7/site-packages/salmon_mail-2-py2.7.egg/salmon/utils.py", line 111, in start_server
    settings = settings_loader()
  File "/Library/Python/2.7/site-packages/salmon_mail-2-py2.7.egg/salmon/commands.py", line 121, in <lambda>
    loader = lambda: utils.import_settings(True, from_dir=os.getcwd(), boot_module=boot)
  File "/Library/Python/2.7/site-packages/salmon_mail-2-py2.7.egg/salmon/utils.py", line 28, in import_settings
    settings = __import__("config.settings", globals(), locals()).settings
ImportError: No module named config.settings
```

Looks like we need a module named config.settings.  Well, that is as far as I can get right now
stay tuned for more fun with Salmon.


Fork
-----

Salmon is a fork of Lamson. In the summer of 2012 (2012-07-13 to be exact),
Lamson was relicenced under a BSD variant that was revokable. The two clauses
that were of most concern:

    4. Contributors agree that any contributions are owned by the copyright holder
    and that contributors have absolutely no rights to their contributions.

    5. The copyright holder reserves the right to revoke this license on anyone who
    uses this copyrighted work at any time for any reason.

I read that to mean that I could make a contribution but then have said work
denied to me because Mr. Shaw didn't like the colour of my socks. So I went and
found the latest version that was available under the GNU GPL version 3.

Salmon is an anagram of Lamson, if you hadn't worked it out already.

Source
-----

You can find the source on GitHub:

https://github.com/moggers87/salmon

Status
------

As this project has only just been forked, there may be bugs that have been
fixed upstream, but can't be backported due to licencing issues.  The source is
well documented, has nearly full test coverage, and runs on Python 2.6 and 2.7.


License
----

Salmon is released under the GNU GPLv3 license, which should be included with
your copy of the source code.  If you didn't receive a copy of the license then
you didn't get the right version of the source code.


Contributing
-------

Pull requests and issues are most welcome.

I will not accept code that has been submitted for inclusion in the original
project, due to the terms of its licence. Unless you have permission from Zed
Shaw.

Testing
=======

The Salmon project needs unit tests, code reviews, coverage information, source
analysis, and security reviews to maintain quality.  If you find a bug, please
take the time to write a test case that fails or provide a piece of mail that
causes the failure.

If you contribute new code then your code should have as much coverage as
possible, with a minimal amount of mocking.


Security
--------

Salmon follows the same security reporting model that has worked for other open
source projects:  If you report a security vulnerability, it will be acted on
immediately and a fix with complete full disclosure will go out to everyone at
the same time.  It's the job of the people using Salmon to keep track of
security relate problems.

Additionally, Salmon is written in as secure a manner as possible and assumes
that it is operating in a hostile environment.  If you find Salmon doesn't
behave correctly given that constraint then please voice your concerns.



Development
===========

Salmon is written entirely in Python and runs on Python 2.6 or 2.7 but not 3k
yet.  It uses only pure Python except where some libraries have compiled
extensions (such as Jinja2).  It should hopefully run on any platform that
supports Python and has Unix semantics.

The code is consistently documented and written to be read in an instructional
manner where possible.  If a piece of code does not make sense, then ask for
help and it will be clarified.  The code is also small and has a full test suite
with about 95% coverage, so you should be able to find out just about anything
you need to hack on Salmon in the Salmon source.

Given the above statements, it should be possible for anyone to take the Salmon
source and read through it in an evening or two.  You should also be able to
understand what's going on, and learn anything you don't by asking questions.

If this isn't the case, then feel free to ask for help understanding it.


