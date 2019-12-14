"""
Documentation for this module can be found in :doc:`commandline`
"""

from __future__ import unicode_literals

from importlib import import_module
import glob
import mailbox
import os
import shutil
import signal
import socket
import sys

import click

from salmon import encoding, mail
from salmon import queue as queue_module
from salmon import routing, server, utils
import salmon

# squash warning about unicode literals. if there are bugs here, then it's
# quite likely to have afffected us before switching to click.
click.disable_unicode_literals_warning = True

DEFAULT_PID_FILE = "./run/smtp.pid"

copyright_notice = """
Salmon is Copyright (C) Matt Molyneaux 2014-2015, 2019.  Licensed GPLv3.
Forked from Lamon, Copyright (C) Zed A. Shaw 2008-2009.  Licensed GPLv3.
If you didn't get a copy of the LICENSE go to:

    https://github.com/moggers87/salmon/LICENSE

Have fun.
"""

uid_desc = """
If you specify a uid/gid then this means you want to first change to
root, set everything up, and then drop to that UID/GID combination.
This is typically so you can bind to port 25 and then become "safe"
to continue operating as a non-root user. If you give one or the other,
this it will just change to that uid or gid without doing the priv drop
operation.
"""


class SalmonCommandError(click.ClickException):
    """Like ClickException, but it doesn't prepend messages with "Error"

    Useful if you want to give a non-zero exit code that's not really an error
    per se
    """
    def show(self, file=None):
        click.echo(self.format_message(), err=True, file=file)


def daemon_start(command, additional_options=[], *args, **kwargs):
    """Wrap a command function with common daemon start parameters"""
    def inner(fn):
        options = additional_options + [
            click.option("--chroot", metavar="PATH", help="path to chroot"),
            click.option("--chdir", metavar="PATH", default=".", help="change to this directory when daemonising"),
            click.option("--umask", metavar="MASK", type=int, help="set umask on server"),
            click.option("--pid", metavar="PATH", default=DEFAULT_PID_FILE, help="path to pid file"),
            click.option("-f", "--force", default=False, is_flag=True, help="force server to run, ignoring pid file"),
            click.option("--debug", default=False, is_flag=True, help="debug mode"),
            click.option("--uid", metavar="UID", type=int, help="run with this user id"),
            click.option("--gid", metavar="GID", type=int, help="run with this group id"),
            click.option("--daemon/--no-daemon", default=True, help="start server as daemon (default)"),
        ]

        for option in reversed(options):
            fn = option(fn)
        kwargs.setdefault("epilog", uid_desc)
        fn = command(*args, **kwargs)(fn)

        return fn
    return inner


@click.group(epilog=copyright_notice)
@click.version_option()
def main():
    """Python mail server"""
    pass


@daemon_start(main.command, additional_options=[
    click.option("--port", metavar="PORT", default=8825, type=int, help="port to listen on"),
    click.option("--host", metavar="ADDRESS", default="127.0.0.1", help="address to listen on"),
], short_help="starts log server")
def log(port, host, pid, chdir, chroot, uid, gid, umask, force, debug, daemon):
    """
    Runs a logging only server on the given hosts and port.  It logs
    each message it receives and also stores it to the run/queue
    so that you can make sure it was received in testing.
    """
    utils.start_server(pid, force, chroot, chdir, uid, gid, umask,
                       lambda: utils.make_fake_settings(host, port), debug, daemon)


@main.command(short_help="send a new email")
@click.option("--port", metavar="PORT", default=8825, type=int, help="Port to connect to")
@click.option("--host", metavar="ADDRESS", default="127.0.0.1", help="Host to connect to")
@click.option("--username", help="SMTP username")
@click.option("--password", help="SMTP password")
@click.option("--sender", metavar="EMAIL")
@click.option("--to", metavar="EMAIL")
@click.option("--subject")
@click.option("--body")
@click.option("--attach")
@click.option("--lmtp", default=False)
@click.option("--ssl", default=False)
@click.option("--starttls", default=False)
def send(port, host, username, password, ssl, starttls, lmtp, sender, to,
         subject, body, attach):
    """
    Sends an email to someone as a test message.
    See the sendmail command for a sendmail replacement.
    """
    message = mail.MailResponse(From=sender, To=to, Subject=subject, Body=body)
    if attach:
        message.attach(attach)

    relay = server.Relay(host, port=port, username=username, password=password, ssl=ssl,
                         starttls=starttls, lmtp=lmtp, debug=False)
    relay.deliver(message)


@main.command(short_help="send an email from stdin")
@click.option("--port", metavar="PORT", default=8825, type=int, help="Port to connect to")
@click.option("--host", metavar="ADDRESS", default="127.0.0.1", help="Address to connect to")
@click.option("--lmtp", default=False, is_flag=True, help="Use LMTP rather than SMTP")
@click.option("--debug", default=False, is_flag=True, help="Debug mode")
@click.argument("recipients", nargs=-1, required=True)
def sendmail(port, host, recipients, debug, lmtp):
    """
    Used as a testing sendmail replacement for use in programs
    like mutt as an MTA.  It reads the email to send on the stdin
    and then delivers it based on the port and host settings.
    """
    relay = server.Relay(host, port=port, debug=debug, lmtp=lmtp)
    data = sys.stdin.read()
    msg = mail.MailRequest(None, recipients, None, data)
    relay.deliver(msg)


@daemon_start(main.command, additional_options=[
    click.option("--boot", metavar="MODULE", default="config.boot", help="module with server definition"),
], short_help="starts a server")
def start(pid, force, chdir, boot, chroot, uid, gid, umask, debug, daemon):
    """
    Runs a salmon server out of the current directory
    """
    utils.start_server(pid, force, chroot, chdir, uid, gid, umask,
                       lambda: utils.import_settings(True, boot_module=boot), debug, daemon)


@main.command(short_help="stops a server")
@click.option("--pid", metavar="PATH", default=DEFAULT_PID_FILE, help="path to pid file")
@click.option("-f", "--force", default=False, is_flag=True, help="force stop server")
@click.option("--all", "all_pids", help="stops all servers with .pid files in the specified directory")
def stop(pid, force, all_pids):
    """
    Stops a running salmon server
    """
    pid_files = []

    if all_pids:
        pid_files = glob.glob(all_pids + "/*.pid")
    else:
        pid_files = [pid]

        if not os.path.exists(pid):
            raise click.FileError(pid, "Maybe Salmon isn't running?")

    click.echo("Stopping processes with the following PID files: %s" % pid_files)

    for pid_f in pid_files:
        with open(pid_f) as pid_file:
            pid_data = pid_file.readline()
            click.echo("Attempting to stop salmon at pid %d" % int(pid_data))

        try:
            if force:
                os.kill(int(pid_data), signal.SIGKILL)
            else:
                os.kill(int(pid_data), signal.SIGHUP)

            os.unlink(pid_f)
        except OSError as exc:
            raise click.ClickException("stopping Salmon on PID %d: %s" % (int(pid_data), exc))


@main.command(short_help="displays status of server")
@click.option("--pid", metavar="PATH", default=DEFAULT_PID_FILE, help="path to pid file")
def status(pid):
    """
    Prints out status information about salmon useful for finding out if it's
    running and where.
    """
    if os.path.exists(pid):
        with open(pid) as pid_file:
            pid_data = pid_file.readline()
            click.echo("Salmon running with PID %d" % int(pid_data))
    else:
        raise SalmonCommandError("Salmon not running.")


@main.command(short_help="manipulate a Queue")
@click.option("--pop", default=False, is_flag=True, help="pop a message from queue")
@click.option("--get", metavar="KEY", help="get key from queue")
@click.option("--remove", metavar="KEY", help="remove chosen key from queue")
@click.option("--count", default=False, is_flag=True, help="count messages in queue")
@click.option("--clear", default=False, is_flag=True, help="clear queue")
@click.option("--keys", default=False, is_flag=True, help="print queue keys")
@click.argument("name", metavar="PATH", default="./run/queue")
def queue(name, pop, get, keys, remove, count, clear):
    """
    Lets you do most of the operations available to a queue.
    """
    click.echo("Using queue: %r" % name)

    inq = queue_module.Queue(name)

    if pop:
        key, msg = inq.pop()
        if key:
            click.echo("KEY: %s" % key)
            click.echo(msg)
    elif get:
        click.echo(inq.get(get))
    elif remove:
        inq.remove(remove)
    elif count:
        click.echo("Queue %s contains %d messages" % (name, len(inq)))
    elif clear:
        inq.clear()
    elif keys:
        click.echo("\n".join(inq.keys()))


@main.command(short_help="display routes")
@click.option("--path", metavar="PATH", default=os.getcwd, help="search path for modules")
@click.option("--test", metavar="EMAIL", help="address to test against routing configuration")
@click.argument("modules", metavar="MODULE", nargs=-1, required=True)
def routes(modules, test, path):
    """
    Prints out valuable information about an application's routing configuration
    after everything is loaded and ready to go.  Helps debug problems with
    messages not getting to your handlers.  Path has the search paths you want
    separated by a ':' character, and it's added to the sys.path.

    MODULE should be a configureation module and can be given multiple times.
    """
    sys.path += path.split(':')
    test_case_matches = []

    utils.import_settings(False)

    for module in modules:
        try:
            import_module(module)
        except ImportError:
            raise click.ClickException("Module '%s' could not be imported. Did you forget to use the --path option?"
                                       % str(module))

    if not routing.Router.REGISTERED:
        raise click.ClickException("Modules '%s' imported, but no function registered." % str(modules))

    # TODO: stop casting everything to str once Python 2.7 support has been dropped
    # we do this to avoid spamming u"blah blah" everywhere
    click.echo("Routing ORDER: %s" % [str(i) for i in routing.Router.ORDER])
    click.echo("Routing TABLE:\n---")
    for format in routing.Router.REGISTERED:
        click.echo("%r: " % str(format), nl=False)
        regex, functions = routing.Router.REGISTERED[format]
        for func in functions:
            click.echo("%s.%s " % (func.__module__, func.__name__), nl=False)
            if test:
                match = regex.match(test)
                if match:
                    test_case_matches.append((str(format), func, match))

        click.echo("\n---")

    if test_case_matches:
        click.echo("\nTEST address %r matches:" % str(test))
        for format, func, match in test_case_matches:
            click.echo("  %r %s.%s" % (format, func.__module__, func.__name__))
            click.echo("  -  %r" % ({str(k): str(v) for k, v in match.groupdict().items()}))
    elif test:
        click.echo("\nTEST address %r didn't match anything." % str(test))
        # don't raise a ClickException because that prepends "ERROR" to the
        # output and this isn't always an error
        sys.exit(1)


@main.command(short_help="generate a new project")
@click.argument("project", metavar="PATH")
@click.option("-f", "--force", is_flag=True, help="overwrite existing directories")
def gen(project, force):
    """
    Generates various useful things for you to get you started.
    """
    template = os.path.join(salmon.__path__[0], "data", "prototype")

    if force:
        shutil.rmtree(project, ignore_errors=True)
    elif os.path.exists(project):
        raise click.ClickException("Project '%s' exists, delete it first." % project)

    shutil.copytree(template, project)


@main.command(short_help="cleanse your emails")
@click.argument("inbox", metavar="IN_MAILBOX")
@click.argument("outbox", metavar="OUT_MAILBOX")
def cleanse(inbox, outbox):
    """
    Uses Salmon mail cleansing and canonicalization system to take an
    input Maildir (or mbox) and replicate the email over into another
    Maildir.  It's used mostly for testing and cleaning.
    """
    error_count = 0

    try:
        inbox = mailbox.mbox(inbox, create=False)
    except (mailbox.Error, IOError):
        try:
            inbox = mailbox.Maildir(inbox, factory=None, create=False)
        except (mailbox.Error, IOError):
            raise click.ClickException("{} does not exist or is not a valid MBox or Maildir".format(inbox))
    outbox = mailbox.Maildir(outbox)

    for msg in inbox:
        try:
            mail = encoding.from_message(msg)
            outbox.add(encoding.to_string(mail))
        except encoding.EncodingError as exc:
            click.echo("ERROR: %s" % exc)
            error_count += 1

    outbox.close()
    inbox.close()

    if error_count > 0:
        raise SalmonCommandError("TOTAL ERRORS: %s" % error_count)
    else:
        click.echo("Completed without errors")


@main.command(short_help="blast emails at a server")
@click.argument("inbox", metavar="MAILBOX")
@click.option("--port", metavar="PORT", default=8823, type=int, help="port to connect to")
@click.option("--host", metavar="ADDRESS", default="127.0.0.1", help="address to connect to")
@click.option("--lmtp", default=False, is_flag=True)
@click.option("--debug", default=False, is_flag=True, help="debug mode")
def blast(inbox, host, port, lmtp, debug):
    """
    Given a Maildir, this command will go through each email
    and blast it at your server.  It does nothing to the message, so
    it will be real messages hitting your server, not cleansed ones.
    """
    try:
        inbox = mailbox.mbox(inbox, create=False)
    except (mailbox.Error, IOError):
        try:
            inbox = mailbox.Maildir(inbox, factory=None, create=False)
        except (mailbox.Error, IOError):
            raise click.ClickException("{} does not exist or is not a valid MBox or Maildir".format(inbox))

    relay = server.Relay(host, port=port, lmtp=lmtp, debug=debug)

    for key in inbox.keys():
        msgfile = inbox.get_file(key)
        msg = encoding.from_file(msgfile)
        try:
            relay.deliver(msg)
        except socket.error as exp:
            raise click.ClickException(str(exp))
        finally:
            msgfile.close()
