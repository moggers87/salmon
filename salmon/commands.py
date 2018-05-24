from __future__ import print_function, unicode_literals

import argparse
import email
import glob
import mailbox
import os
import shutil
import signal
import sys

from salmon import server, utils, mail, routing, queue, encoding
import salmon


COMMANDS = (
    ("start", "starts a server"),
    ("stop", "stops a server"),
    ("status", "displays status of server"),
    ("gen", "generate new project"),
    ("log", "start log server"),
    ("queue", "manipulate a Queue"),
    ("blast", "blast emails at a server"),
    ("cleanse", "cleanse your emails"),
    ("routes", "display routes"),
    ("send", "send a new email"),
    ("sendmail", "send an email from stdin"),
)

DEFAULT_PID_FILE = "./run/stmp.pid"

version_info = """
Salmon-Version:  %s
Version-File:  %s
""" % (salmon.__version__, salmon.__file__)

copyright_notice = """
Salmon is Copyright (C) Matt Molyneaux 2014-2015.  Licensed GPLv3.
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


def main():
    """Salmon script entry point"""
    args = _parser.parse_args()

    # get function reference from args and then remove it
    cmd = args.func
    del args.func

    # pass all other attrs to function as kwargs
    cmd(**vars(args))


def log_command(parser):
    """
    Runs a logging only server on the given hosts and port.  It logs
    each message it receives and also stores it to the run/queue
    so that you can make sure it was received in testing.
    """
    def command(port, host, pid, chdir, chroot=None, uid=False, gid=False, umask=False,
                force=False, debug=False, daemon=True):
        utils.start_server(pid, force, chroot, chdir, uid, gid, umask,
                           lambda: utils.make_fake_settings(host, port), debug, daemon)

    parser.set_defaults(func=command)

    parser.add_argument("--port", default=8825, type=int, help="port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="address to listen on")
    parser.add_argument("--chroot", default=argparse.SUPPRESS, help="path to chroot")
    parser.add_argument("--chdir", default=".", help="change to this directory when daemonising")
    parser.add_argument("--umask", type=int, default=argparse.SUPPRESS, help="set umask on server")
    parser.add_argument("--pid", default="./run/log.pid", help="path to pid file")
    parser.add_argument("-f", "--force", action="store_true", help="force server to run, ignoring pid file")
    parser.add_argument("--debug", action="store_true", default=argparse.SUPPRESS, help="debug mode")

    uid_group = parser.add_argument_group(title="UID/GID options", description=uid_desc)
    uid_group.add_argument("--uid", type=int, default=argparse.SUPPRESS, help="run with this user id")
    uid_group.add_argument("--gid", type=int, default=argparse.SUPPRESS, help="run with this group id")

    daemon_group = parser.add_mutually_exclusive_group()
    daemon_group.add_argument("--no-daemon", default=argparse.SUPPRESS, dest="daemon", action="store_false",
                              help="start server in foreground")
    daemon_group.add_argument("--daemon", default=argparse.SUPPRESS, dest="daemon", action="store_true",
                              help="start server as daemon (default)")


def send_command(parser):
    """
    Sends an email to someone as a test message.
    See the sendmail command for a sendmail replacement.
    """
    def command(port, host, username=None, password=None, ssl=None, starttls=None, lmtp=None,
                sender=None, to=None, subject=None, body=None, attach=None):
        message = mail.MailResponse(From=sender, To=to, Subject=subject, Body=body)
        if attach:
            message.attach(attach)

        relay = server.Relay(host, port=port, username=username, password=password, ssl=ssl,
                             starttls=starttls, lmtp=lmtp, debug=False)
        relay.deliver(message)

    parser.set_defaults(func=command)

    parser.add_argument("--port", default=8825, type=int, help="port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="address to listen on")
    parser.add_argument("--username", default=argparse.SUPPRESS, help="SMTP username")
    parser.add_argument("--password", default=argparse.SUPPRESS, help="SMTP password")
    parser.add_argument("--sender", metavar="EMAIL", default=argparse.SUPPRESS)
    parser.add_argument("--to", metavar="EMAIL", default=argparse.SUPPRESS)
    parser.add_argument("--subject", default=argparse.SUPPRESS)
    parser.add_argument("--body", default=argparse.SUPPRESS)
    parser.add_argument("--attach", default=argparse.SUPPRESS)
    parser.add_argument("--lmtp", action="store_true", default=argparse.SUPPRESS)

    tls_group = parser.add_mutually_exclusive_group()
    tls_group.add_argument("--ssl", action="store_true", default=argparse.SUPPRESS)
    tls_group.add_argument("--starttls", action="store_true", default=argparse.SUPPRESS)


def sendmail_command(parser):
    """
    Used as a testing sendmail replacement for use in programs
    like mutt as an MTA.  It reads the email to send on the stdin
    and then delivers it based on the port and host settings.
    """
    def command(port, host, recipients, debug=False, lmtp=False):
        relay = server.Relay(host, port=port, debug=debug, lmtp=lmtp)
        data = sys.stdin.read()
        msg = mail.MailRequest(None, recipients, None, data)
        relay.deliver(msg)

    parser.set_defaults(func=command)

    parser.add_argument("--port", default=8825, type=int, help="Port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="Address to listen on")
    parser.add_argument("--lmtp", action="store_true", default=argparse.SUPPRESS, help="Use LMTP rather than SMTP")
    parser.add_argument("--debug", action="store_true", default=argparse.SUPPRESS, help="Debug mode")
    parser.add_argument("recipients", action="append")


def start_command(parser):
    """
    Runs a salmon server out of the current directory
    """
    def command(pid, force, chdir, boot, chroot=False, uid=False, gid=False, umask=False, debug=False, daemon=True):
        utils.start_server(pid, force, chroot, chdir, uid, gid, umask,
                           lambda: utils.import_settings(True, boot_module=boot), debug, daemon)

    parser.set_defaults(func=command)

    parser.add_argument("--boot", default="config.boot", help="module with server definition")
    parser.add_argument("--chroot", default=argparse.SUPPRESS, help="path to chroot")
    parser.add_argument("--chdir", default=".", help="change to this directory when daemonising")
    parser.add_argument("--umask", type=int, default=argparse.SUPPRESS, help="set umask on server")
    parser.add_argument("--pid", default=DEFAULT_PID_FILE, help="path to pid file")
    parser.add_argument("-f", "--force", action="store_true", help="force server to run, ignoring pid file")
    parser.add_argument("--debug", action="store_true", default=argparse.SUPPRESS, help="debug mode")

    uid_group = parser.add_argument_group(title="UID/GID options", description=uid_desc)
    uid_group.add_argument("--uid", type=int, default=argparse.SUPPRESS, help="run with this user id")
    uid_group.add_argument("--gid", type=int, default=argparse.SUPPRESS, help="run with this group id")

    daemon_group = parser.add_mutually_exclusive_group()
    daemon_group.add_argument("--no-daemon", default=argparse.SUPPRESS, dest="daemon", action="store_false",
                              help="start server in foreground")
    daemon_group.add_argument("--daemon", default=argparse.SUPPRESS, dest="daemon", action="store_true",
                              help="start server as daemon (default)")


def stop_command(parser):
    """
    Stops a running salmon server
    """
    def command(pid, kill=False, all=False):
        pid_files = []

        if all:
            pid_files = glob.glob(all + "/*.pid")
        else:
            pid_files = [pid]

            if not os.path.exists(pid):
                print("PID file %s doesn't exist, maybe Salmon isn't running?" % pid)
                sys.exit(1)
                return  # for unit tests mocking sys.exit

        print("Stopping processes with the following PID files: %s" % pid_files)

        for pid_f in pid_files:
            pid = open(pid_f).readline()

            print("Attempting to stop salmon at pid %d" % int(pid))

            try:
                if kill:
                    os.kill(int(pid), signal.SIGKILL)
                else:
                    os.kill(int(pid), signal.SIGHUP)

                os.unlink(pid_f)
            except OSError as exc:
                print("ERROR stopping Salmon on PID %d: %s" % (int(pid), exc))

    parser.set_defaults(func=command)

    parser.add_argument("--pid", default=DEFAULT_PID_FILE, help="path to pid file")
    parser.add_argument("-f", "--force", dest="kill", default=DEFAULT_PID_FILE, action="store_true",
                        help="force stop server")
    parser.add_argument("--all", default=argparse.SUPPRESS,
                        help="stops all servers with .pid files in the specified directory")


def status_command(parser):
    """
    Prints out status information about salmon useful for finding out if it's
    running and where.
    """
    def command(pid):
        if os.path.exists(pid):
            pid = open(pid).readline()
            print("Salmon running with PID %d" % int(pid))
        else:
            print("Salmon not running.")

    parser.set_defaults(func=command)

    parser.add_argument("--pid", default=DEFAULT_PID_FILE, help="path to pid file")


def queue_command(parser):
    """
    Lets you do most of the operations available to a queue.
    """
    def command(name, pop=False, get=False, keys=False, remove=False, count=False, clear=False):
        print("Using queue: %r" % name)

        inq = queue.Queue(name)

        if pop:
            key, msg = inq.pop()
            if key:
                print("KEY: %s" % key)
                print(msg)
        elif get:
            print(inq.get(get))
        elif remove:
            inq.remove(remove)
        elif count:
            print("Queue %s contains %d messages" % (name, inq.count()))
        elif clear:
            inq.clear()
        elif keys:
            print("\n".join(inq.keys()))

    parser.set_defaults(func=command)

    command_group = parser.add_mutually_exclusive_group(required=True)
    command_group.add_argument("--pop", action="store_true", default=argparse.SUPPRESS,
                               help="pop a message from queue")
    command_group.add_argument("--get", metavar="KEY", default=argparse.SUPPRESS, help="get key from queue")
    command_group.add_argument("--remove", metavar="KEY", default=argparse.SUPPRESS,
                               help="remove chosen key from queue")
    command_group.add_argument("--count", action="store_true", default=argparse.SUPPRESS,
                               help="count messages in queue")
    command_group.add_argument("--clear", action="store_true", default=argparse.SUPPRESS, help="clear queue")
    command_group.add_argument("--keys", action="store_true", default=argparse.SUPPRESS, help="print queue keys")

    parser.add_argument("name", nargs="?", default="./run/queue", help="path of queue", metavar="queue")


def routes_command(parser):
    """
    Prints out valuable information about an application's routing configuration
    after everything is loaded and ready to go.  Helps debug problems with
    messages not getting to your handlers.  Path has the search paths you want
    separated by a ':' character, and it's added to the sys.path.
    """
    def command(modules, path=os.getcwd(), test=""):
        sys.path += path.split(':')
        test_case_matches = []

        for module in modules:
            __import__(module, globals(), locals())

        print("Routing ORDER: ", routing.Router.ORDER)
        print("Routing TABLE: \n---")
        for format in routing.Router.REGISTERED:
            print("%r: " % format, end="")
            regex, functions = routing.Router.REGISTERED[format]
            for func in functions:
                print("%s.%s " % (func.__module__, func.__name__), end="")
                match = regex.match(test)
                if test and match:
                    test_case_matches.append((format, func, match))

            print("\n---")

        if test_case_matches:
            print("\nTEST address %r matches:" % test)
            for format, func, match in test_case_matches:
                print("  %r %s.%s" % (format, func.__module__, func.__name__))
                print("  -  %r" % (match.groupdict()))
        elif test:
            print("\nTEST address %r didn't match anything." % test)

    parser.set_defaults(func=command)

    parser.add_argument("--path", default=argparse.SUPPRESS, help="search path for modules")
    parser.add_argument("modules", metavar="module", nargs="*", default=["config.testing"],
                        help="config modules to process")
    parser.add_argument("--test", metavar="EMAIL", default=argparse.SUPPRESS, help="test address")


def gen_command(parser):
    """
    Generates various useful things for you to get you started.
    """
    def command(project, force=False):
        template = os.path.join(salmon.__path__[0], "data", "prototype")

        if os.path.exists(project) and not force:
            print("Project %s exists, delete it first." % project)
            sys.exit(1)
            return
        elif force:
            shutil.rmtree(project, ignore_errors=True)

        shutil.copytree(template, project)

    parser.set_defaults(func=command)

    parser.add_argument("project", help="project name")
    parser.add_argument("-f", "--force", action="store_true", default=argparse.SUPPRESS,
                        help="overwrite existing directories")


def cleanse_command(parser):
    """
    Uses Salmon mail cleansing and canonicalization system to take an
    input Maildir (or mbox) and replicate the email over into another
    Maildir.  It's used mostly for testing and cleaning.
    """
    def command(input, output):
        error_count = 0

        try:
            inbox = mailbox.mbox(input)
        except IOError:
            inbox = mailbox.Maildir(input, factory=None)

        outbox = mailbox.Maildir(output)

        for msg in inbox:
            try:
                mail = encoding.from_message(msg)
                outbox.add(encoding.to_string(mail))
            except encoding.EncodingError as exc:
                print("ERROR: %s" % exc)
                error_count += 1

        outbox.close()
        inbox.close()

        print("TOTAL ERRORS: %s" % error_count)

    parser.set_defaults(func=command)

    parser.add_argument("input", help="input Maildir or mbox")
    parser.add_argument("output", help="output Maildir")


def blast_command(parser):
    """
    Given a Maildir, this command will go through each email
    and blast it at your server.  It does nothing to the message, so
    it will be real messages hitting your server, not cleansed ones.
    """
    def command(input, host, port, lmtp=None, debug=False):
        try:
            inbox = mailbox.mbox(input)
        except IOError:
            inbox = mailbox.Maildir(input, factory=None)

        relay = server.Relay(host, port=port, lmtp=lmtp, debug=debug)

        for key in inbox.keys():
            msgfile = inbox.get_file(key)
            msg = email.message_from_file(msgfile)
            relay.deliver(msg)

    parser.set_defaults(func=command)

    parser.add_argument("input", help="input Maildir or mbox")
    parser.add_argument("--port", default=8823, type=int, help="port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="address to listen on")
    parser.add_argument("--lmtp", action="store_true", default=argparse.SUPPRESS)
    parser.add_argument("--debug", action="store_true", default=argparse.SUPPRESS, help="debug mode")


# Bring it all together

_parser = argparse.ArgumentParser(description="Python mail server", epilog=copyright_notice,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)

_parser.add_argument("-v", "--version", action="version", version=version_info)
_subparsers = _parser.add_subparsers(metavar="<command>")
_subparsers.required = True

for cmd, help_txt in COMMANDS:
    function = globals()["{0}_command".format(cmd)]
    cmd_parser = _subparsers.add_parser(cmd, description=function.__doc__, help=help_txt,
                                        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    function(cmd_parser)
