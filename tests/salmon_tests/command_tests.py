import os
import shutil
import sys

from mock import Mock, patch
from nose.tools import assert_equal, assert_not_equal, raises, with_setup

from salmon import commands, utils, mail, routing, encoding

from .setup_env import setup_salmon_dirs, teardown_salmon_dirs


def setup():
    if os.path.exists("run/fake.pid"):
        os.unlink("run/fake.pid")


def teardown():
    if os.path.exists("run/fake.pid"):
        os.unlink("run/fake.pid")


def make_fake_pid_file():
    f = open("run/fake.pid", "w")
    f.write("0")
    f.close()


def get_command(command):
    def func(*args):
        args = list(args)
        args.insert(0, command)

        parsed_args = commands._parser.parse_args(args)

        cmd = parsed_args.func
        del parsed_args.func

        cmd(**vars(parsed_args))

    return func


def test_send_command():
    command = get_command("send")
    command("--sender", 'test@localhost', "--to", 'test@localhost', "--body",
            'Test body', "--subject", 'Test subject', "--attach", 'setup.py', "--port",
            "8899", "--host", "127.0.0.1")


def test_status_command():
    command = get_command("status")
    command("--pid", 'run/log.pid')
    command("--pid", 'run/donotexist.pid')


@patch('sys.argv', ['salmon'])
@raises(SystemExit)
def test_main():
    commands.main()


@patch('salmon.queue.Queue')
@patch('sys.exit', new=Mock())
def test_queue_command(MockQueue):
    mq = MockQueue()
    mq.get.return_value = "A sample message"
    mq.keys.return_value = ["key1", "key2"]
    mq.pop.return_value = ('key1', 'message1')
    mq.count.return_value = 1

    command = get_command("queue")

    command("--pop")
    assert mq.pop.called

    command("--get", 'somekey')
    assert mq.get.called

    command("--remove", 'somekey')
    assert mq.remove.called

    command("--clear")
    assert mq.clear.called

    command("--keys")
    assert mq.keys.called

    command("--count")
    assert mq.count.called


@patch('sys.exit', new=Mock())
def test_gen_command():
    command = get_command("gen")
    project = 'tests/testproject'
    if os.path.exists(project):
        shutil.rmtree(project)

    command(project)
    assert os.path.exists(project)

    # test that it exits if the project exists
    command(project)
    assert_equal(sys.exit.call_args, ((1,),))

    sys.exit.reset_mock()
    command(project, "--force")
    assert_not_equal(sys.exit.call_args, ((1,),))

    # TODO: put this in a tear down
    shutil.rmtree(project)


def test_routes_command():
    command = get_command("routes")
    command('salmon.handlers.log', 'salmon.handlers.queue')

    # test with the --test option
    command('salmon.handlers.log', 'salmon.handlers.queue', "--test", "anything@localhost")

    # test with the -test option but no matches
    routing.Router.clear_routes()
    command("--test", "anything@localhost")


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
@patch('sys.exit', new=Mock())
@patch('salmon.utils.daemonize', new=Mock())
@patch('salmon.server.SMTPReceiver')
def test_log_command(MockSMTPReceiver):
    command = get_command("log")
    ms = MockSMTPReceiver()
    ms.start.function()

    setup()  # make sure it's clear for fake.pid
    command("--host", "127.0.0.1", "--port", "8825", "--pid", "run/fake.pid")
    assert utils.daemonize.called
    assert ms.start.called

    # test that it exits on existing pid
    make_fake_pid_file()
    command("--host", "127.0.0.1", "--port", "8825", "--pid", "run/fake.pid")
    assert sys.exit.called


@patch('sys.stdin', new=Mock())
def test_sendmail_command():
    sys.stdin.read.function()

    msg = mail.MailResponse(To="tests@localhost", From="tests@localhost",
                            Subject="Hello", Body="Test body.")
    sys.stdin.read.return_value = str(msg)

    command = get_command("sendmail")
    command("--host", "127.0.0.1", "--port", "8899", "test@localhost")


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
@patch('sys.exit', new=Mock())
@patch('salmon.utils.daemonize', new=Mock())
@patch('salmon.utils.import_settings', new=Mock())
@patch('salmon.utils.drop_priv', new=Mock())
@patch('sys.path', new=Mock())
def test_start_command():
    # normal start
    command = get_command("start")
    command("--pid", "smtp.pid")
    assert utils.daemonize.call_count == 1
    assert utils.import_settings.called

    # start with pid file existing already
    make_fake_pid_file()
    command("--pid", "run/fake.pid")
    assert sys.exit.called

    # start with pid file existing and force given
    assert os.path.exists("run/fake.pid")
    command("--force", "--pid", "run/fake.pid")
    assert not os.path.exists("run/fake.pid")

    # start with a uid but no gid
    command("--uid", "1000", "--pid", "run/fake.pid", "--force")
    assert not utils.drop_priv.called

    # start with a uid/gid given that's valid
    command("--uid", "1000", "--gid", "1000", "--pid", "run/fake.pid", "--force")
    assert utils.drop_priv.called

    # non daemon start
    daemonize_call_count = utils.daemonize.call_count
    command("--pid", "run/fake.pid", "--no-daemon", "--force")
    assert utils.daemonize.call_count == daemonize_call_count  # same count -> not called


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
@patch('sys.exit', new=Mock())
@patch('os.kill', new=Mock())
@patch('glob.glob', new=lambda x: ['run/fake.pid'])
def test_stop_command():
    command = get_command("stop")
    # gave a bad pid file
    try:
        command("--pid", "run/dontexit.pid")
    except IOError:
        assert sys.exit.called

    make_fake_pid_file()
    command("--pid", "run/fake.pid")

    make_fake_pid_file()
    command("--all", "run")

    make_fake_pid_file()
    command("--pid", "run/fake.pid", "--force")
    assert os.kill.called
    assert not os.path.exists("run/fake.pid")

    make_fake_pid_file()
    os.kill.side_effect = OSError("Fail")
    command("--pid", "run/fake.pid", "--force")


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
def test_cleanse_command():
    command = get_command("cleanse")
    command('run/queue', 'run/cleansed')
    assert os.path.exists('run/cleansed')


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
@patch('salmon.encoding.from_message')
def test_cleans_command_with_encoding_error(from_message):
    command = get_command("cleanse")
    from_message.side_effect = encoding.EncodingError
    command('run/queue', 'run/cleansed')


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
def test_blast_command():
    command = get_command("blast")
    command("--host", "127.0.0.1", "--port", "8899", "run/queue")
