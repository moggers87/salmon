import shutil
import mailbox
import os

from mock import Mock, patch
from nose.tools import assert_equal, raises, with_setup

from salmon import queue, mail

from .setup_env import setup_salmon_dirs, teardown_salmon_dirs


USE_SAFE = False


def setup():
    if os.path.exists("run/big_queue"):
        shutil.rmtree("run/big_queue")


def teardown():
    setup()


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
def test_push():
    q = queue.Queue("run/queue", safe=USE_SAFE)
    q.clear()

    # the queue doesn't really care if its a request or response, as long
    # as the object answers to str(msg)
    msg = mail.MailResponse(To="test@localhost", From="test@localhost", Subject="Test", Body="Test")
    key = q.push(msg)

    assert key, "Didn't get a key for test_get push."

    return q


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
def test_pop():
    q = test_push()
    key, msg = q.pop()

    assert key, "Didn't get a key for test_get push."
    assert msg, "Didn't get a message for key %r" % key

    assert hasattr(msg, "Data"), "MailRequest doesn't have Data attribute"

    assert_equal(msg['to'], "test@localhost")
    assert_equal(msg['from'], "test@localhost")
    assert_equal(msg['subject'], "Test")
    assert_equal(msg.body(), "Test")

    assert_equal(q.count(), 0)
    assert not q.pop()[0]


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
def test_get():
    q = test_push()
    msg = mail.MailResponse(To="test@localhost", From="test@localhost", Subject="Test", Body="Test")

    key = q.push(str(msg))
    assert key, "Didn't get a key for test_get push."

    msg = q.get(key)
    assert msg, "Didn't get a message for key %r" % key


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
def test_remove():
    q = test_push()
    msg = mail.MailResponse(To="test@localhost", From="test@localhost", Subject="Test", Body="Test")

    key = q.push(str(msg))
    assert key, "Didn't get a key for test_get push."
    assert_equal(q.count(), 2)

    q.remove(key)
    assert_equal(q.count(), 1)


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
def test_safe_maildir():
    global USE_SAFE
    USE_SAFE = True
    test_push()
    test_pop()
    test_get()
    test_remove()


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
def test_oversize_protections():
    # first just make an oversize limited queue
    overq = queue.Queue("run/queue", pop_limit=10)
    overq.clear()

    for i in range(5):
        overq.push("HELLO" * 100)

    assert_equal(overq.count(), 5)

    key, msg = overq.pop()

    assert not key and not msg, "Should get no messages."
    assert_equal(overq.count(), 0)

    # now make sure that oversize mail is moved to the overq
    setup()
    overq = queue.Queue("run/queue", pop_limit=10, oversize_dir="run/big_queue")
    moveq = queue.Queue("run/big_queue")

    for i in range(5):
        overq.push("HELLO" * 100)

    key, msg = overq.pop()

    assert not key and not msg, "Should get no messages."
    assert_equal(overq.count(), 0)
    assert_equal(moveq.count(), 5)

    moveq.clear()
    overq.clear()


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
@patch('os.stat', new=Mock())
@raises(mailbox.ExternalClashError)
def test_SafeMaildir_name_clash():
    sq = queue.SafeMaildir('run/queue')
    sq.add("TEST")


def raise_OSError(*x, **kw):
    err = OSError('Fail')
    err.errno = 0
    raise err


@patch('mailbox._create_carefully', new=Mock())
@raises(OSError)
def test_SafeMaildir_throws_errno_failure():
    setup()
    mailbox._create_carefully.side_effect = raise_OSError
    sq = queue.SafeMaildir('run/queue')
    sq.add("TEST")


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
@patch('os.stat', new=Mock())
@raises(OSError)
def test_SafeMaildir_reraise_weird_errno():
    os.stat.side_effect = raise_OSError
    sq = queue.SafeMaildir('run/queue')
    sq.add('TEST')
