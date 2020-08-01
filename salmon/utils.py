"""
Mostly utility functions Salmon uses internally that don't
really belong anywhere else in the modules.  This module
is kind of a dumping ground, so if you find something that
can be improved feel free to work up a patch.
"""
import imp
import importlib
import logging
import os
import sys

from lockfile import pidlockfile
import daemon

from salmon import routing, server

settings = None


def import_settings(boot_also, boot_module="config.boot"):
    """Returns the current settings module, there is no harm in calling it
    multiple times

    The location of the settings module can be control via
    ``SALMON_SETTINGS_MODULE``"""
    global settings

    if settings is None:
        settings_module = os.getenv("SALMON_SETTINGS_MODULE", "config.settings")
        settings = importlib.import_module(settings_module)

    if boot_also:
        importlib.import_module(boot_module)

    return settings


def daemonize(pid, chdir, chroot, umask, files_preserve=None, do_open=True):
    """
    Uses python-daemonize to do all the junk needed to make a
    server a server.  It supports all the features daemonize
    has, except that chroot probably won't work at all without
    some serious configuration on the system.
    """
    logs_dir = os.path.join(chdir, "logs")
    pid_dir = os.path.join(chdir, os.path.dirname(pid) or ".")
    if chroot:
        logs_dir = os.path.join(chroot, logs_dir)
        pid_dir = os.path.join(chroot, pid_dir)
    if not os.path.exists(logs_dir):
        os.mkdir(logs_dir)
    if not os.path.exists(pid_dir):
        os.mkdir(pid_dir)

    context = daemon.DaemonContext()
    context.pidfile = pidlockfile.PIDLockFile(pid)
    context.stdout = open(os.path.join(logs_dir, "salmon.out"), "a+")
    context.stderr = open(os.path.join(logs_dir, "salmon.err"), "a+")
    context.files_preserve = files_preserve or []
    context.working_directory = os.path.expanduser(chdir)

    if chroot:
        context.chroot_directory = os.path.expanduser(chroot)
    if umask is not None:
        context.umask = umask

    if do_open:
        context.open()

    return context


def drop_priv(uid, gid):
    """
    Changes the uid/gid to the two given, you should give utils.daemonize
    0,0 for the uid,gid so that it becomes root, which will allow you to then
    do this.
    """
    logging.debug("Dropping to uid=%d, gid=%d", uid, gid)
    daemon.daemon.change_process_owner(uid, gid)
    logging.debug("Now running as uid=%d, gid=%d", os.getgid(), os.getuid())


def make_fake_settings(host, port):
    """
    When running as a logging server we need a fake settings module to work with
    since the logging server can be run in any directory, so there may not be
    a settings module to import.
    """
    global settings

    if settings is None:
        logging.basicConfig(filename="logs/logger.log", level=logging.DEBUG)
        routing.Router.load(['salmon.handlers.log', 'salmon.handlers.queue'])
        settings = imp.new_module('settings')
        settings.receiver = server.AsyncSMTPReceiver(hostname=host, port=port)
        settings.relay = None
        logging.info("Logging mode enabled, will not send email to anyone, just log.")

    return settings


def check_for_pid(pid, force):
    """Checks if a pid file is there, and if it is sys.exit.  If force given
    then it will remove the file and not exit if it's there."""
    if os.path.exists(pid):
        if not force:
            print("PID file %s exists, so assuming Salmon is running.  Give --force to force it to start." % pid)
            sys.exit(1)
        else:
            os.unlink(pid)


def start_server(pid, force, chroot, chdir, uid, gid, umask, settings_loader, debug, daemon_proc):
    """
    Starts the server by doing a daemonize and then dropping priv
    accordingly.  It will only drop to the uid/gid given if both are given.
    """
    check_for_pid(pid, force)

    if not debug and daemon_proc:
        daemonize(pid, chdir, chroot, umask, files_preserve=[])

    sys.path.append(os.getcwd())

    settings = settings_loader()

    if uid and gid:
        drop_priv(uid, gid)
    elif uid or gid:
        logging.warning("You probably meant to give a uid and gid, but you gave: uid=%r, gid=%r. "
                        "Will not change to any user.", uid, gid)

    settings.receiver.start()

    if debug:
        print("Salmon started in debug mode. ctrl-c to quit...")
        import time
        try:
            while True:
                time.sleep(100000)
        except KeyboardInterrupt:
            # hard quit, since receiver starts a new thread. dirty but works
            os._exit(1)
