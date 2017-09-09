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


@patch("salmon.server.smtplib.SMTP")
def test_send_command(client_mock):
    command = get_command("send")
    command("--sender", 'test@localhost', "--to", 'test@localhost', "--body",
            'Test body', "--subject", 'Test subject', "--attach", 'setup.py', "--port",
            "8899", "--host", "127.0.0.1")
    assert_equal(client_mock.return_value.sendmail.call_count, 1)


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
    assert_equal(mq.pop.call_count, 1)

    command("--get", 'somekey')
    assert_equal(mq.get.call_count, 1)

    command("--remove", 'somekey')
    assert_equal(mq.remove.call_count, 1)

    command("--clear")
    assert_equal(mq.clear.call_count, 1)

    command("--keys")
    assert_equal(mq.keys.call_count, 1)

    command("--count")
    assert_equal(mq.count.call_count, 1)


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
    assert_equal(utils.daemonize.call_count, 1)
    assert_equal(ms.start.call_count, 1)

    # test that it exits on existing pid
    make_fake_pid_file()
    command("--host", "127.0.0.1", "--port", "8825", "--pid", "run/fake.pid")
    assert_equal(sys.exit.call_count, 1)


@patch('sys.stdin', new=Mock())
@patch("salmon.server.smtplib.SMTP")
def test_sendmail_command(client_mock):
    sys.stdin.read.function()

    msg = mail.MailResponse(To="tests@localhost", From="tests@localhost",
                            Subject="Hello", Body="Test body.")
    sys.stdin.read.return_value = str(msg)

    command = get_command("sendmail")
    command("--host", "127.0.0.1", "--port", "8899", "test@localhost")
    assert_equal(client_mock.return_value.sendmail.call_count, 1)


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
    assert_equal(utils.daemonize.call_count, 1)
    assert_equal(utils.import_settings.call_count, 1)

    # start with pid file existing already
    make_fake_pid_file()
    command("--pid", "run/fake.pid")
    assert_equal(sys.exit.call_count, 1)

    # start with pid file existing and force given
    assert os.path.exists("run/fake.pid")
    command("--force", "--pid", "run/fake.pid")
    assert not os.path.exists("run/fake.pid")

    # start with a uid but no gid
    command("--uid", "1000", "--pid", "run/fake.pid", "--force")
    assert_equal(utils.drop_priv.call_count, 0)

    # start with a uid/gid given that's valid
    command("--uid", "1000", "--gid", "1000", "--pid", "run/fake.pid", "--force")
    assert_equal(utils.drop_priv.call_count, 1)

    # non daemon start
    daemonize_call_count = utils.daemonize.call_count
    command("--pid", "run/fake.pid", "--no-daemon", "--force")
    assert_equal(utils.daemonize.call_count, daemonize_call_count)  # same count -> not called


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
@patch('sys.exit', new=Mock())
@patch('os.kill', new=Mock())
@patch('glob.glob', new=lambda x: ['run/fake.pid'])
def test_stop_command():
    command = get_command("stop")
    # gave a bad pid file
    command("--pid", "run/dontexit.pid")
    assert_equal(sys.exit.call_count, 1)

    make_fake_pid_file()
    command("--pid", "run/fake.pid")

    make_fake_pid_file()
    command("--all", "run")

    os_kill_count = os.kill.call_count
    make_fake_pid_file()
    command("--pid", "run/fake.pid", "--force")
    assert_equal(os.kill.call_count, os_kill_count + 1)  # kill should have been called once more
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
