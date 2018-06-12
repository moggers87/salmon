import os
import smtplib
import subprocess
import time

from nose.tools import with_setup, assert_equal
from salmon import queue

from .setup_env import setup_salmon_dirs, teardown_salmon_dirs
from config import settings as server_settings


_server = None


def setup():
    global _server
    env = os.environ.copy()
    env["PYTHONPATH"] = "tests"
    _server = subprocess.Popen(["salmon", "start", "--boot", "config.dump", "--no-daemon"], env=env)
    for i in range(5):
        try:
            conn = smtplib.SMTP(**server_settings.receiver_config)
        except Exception:
            time.sleep(2**i)
            continue
        else:
            conn.quit()
            return

    raise Exception("Server still not ready, something must be wrong")


def teardown():
    global _server
    _server.kill()
    _server = None


def setup_salmon_dirs_with_queues():
    setup_salmon_dirs()
    # re-create destoryed queues
    queue.Queue(server_settings.UNDELIVERABLE_QUEUE)
    queue.Queue(server_settings.QUEUE_PATH)


@with_setup(setup_salmon_dirs_with_queues, teardown_salmon_dirs)
def test_we_get_message():
    client = smtplib.SMTP(**server_settings.receiver_config)

    client.helo()
    client.sendmail("me@example.com", "you@example.com", "hello")

    undelivered = queue.Queue(server_settings.UNDELIVERABLE_QUEUE)
    assert_equal(len(undelivered.mbox), 0)

    inbox = queue.Queue(server_settings.QUEUE_PATH)
    assert_equal(len(inbox.mbox), 1)


@with_setup(setup_salmon_dirs_with_queues, teardown_salmon_dirs)
def test_we_dont_get_message():
    client = smtplib.SMTP(**server_settings.receiver_config)

    client.helo()
    client.sendmail("me@example.com", "you@example1.com", "hello")

    undelivered = queue.Queue(server_settings.UNDELIVERABLE_QUEUE)
    assert_equal(len(undelivered.mbox), 1)

    inbox = queue.Queue(server_settings.QUEUE_PATH)
    assert_equal(len(inbox.mbox), 0)
