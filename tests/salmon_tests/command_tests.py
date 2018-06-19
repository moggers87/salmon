import os
import shutil
import sys

from click import testing
from mock import Mock, patch

from nose.tools import assert_equal, with_setup
from salmon import commands, encoding, mail, routing, utils

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


class CliRunner(testing.CliRunner):
    def invoke(self, *args, **kwargs):
        kwargs.setdefault("catch_exceptions", False)
        return super(CliRunner, self).invoke(*args, **kwargs)


@patch("salmon.server.smtplib.SMTP")
def test_send_command(client_mock):
    runner = CliRunner()
    runner.invoke(commands.main, ("send", "--sender", "test@localhost", "--to", "test@localhost",
                                  "--body", "Test body", "--subject", "Test subject", "--attach",
                                  "setup.py", "--port", "8899", "--host", "127.0.0.1"))
    assert_equal(client_mock.return_value.sendmail.call_count, 1)


def test_status_command():
    runner = CliRunner()
    runner.invoke(commands.main, ("status", "--pid", 'run/log.pid'))
    runner.invoke(commands.main, ("status", "--pid", 'run/donotexist.pid'))


def test_main():
    runner = CliRunner()
    runner.invoke(commands.main)


@patch('salmon.queue.Queue')
def test_queue_command(MockQueue):
    mq = MockQueue()
    mq.get.return_value = "A sample message"
    mq.keys.return_value = ["key1", "key2"]
    mq.pop.return_value = ('key1', 'message1')
    mq.count.return_value = 1

    runner = CliRunner()

    runner.invoke(commands.main, ("queue", "--pop"))
    assert_equal(mq.pop.call_count, 1)

    runner.invoke(commands.main, ("queue", "--get", "somekey"))
    assert_equal(mq.get.call_count, 1)

    runner.invoke(commands.main, ("queue", "--remove", "somekey"))
    assert_equal(mq.remove.call_count, 1)

    runner.invoke(commands.main, ("queue", "--clear"))
    assert_equal(mq.clear.call_count, 1)

    runner.invoke(commands.main, ("queue", "--keys"))
    assert_equal(mq.keys.call_count, 1)

    runner.invoke(commands.main, ("queue", "--count"))
    assert_equal(mq.count.call_count, 1)


def test_gen_command():
    runner = CliRunner()
    project = 'tests/testproject'
    if os.path.exists(project):
        shutil.rmtree(project)

    result = runner.invoke(commands.main, ("gen", project))
    assert os.path.exists(project)
    assert_equal(result.exit_code, 0)

    # test that it exits if the project exists
    result = runner.invoke(commands.main, ("gen", project))
    assert_equal(result.exit_code, 1)

    result = runner.invoke(commands.main, ("gen", project, "--force"))
    assert_equal(result.exit_code, 0)

    # TODO: put this in a tear down
    shutil.rmtree(project)


def test_routes_command():
    runner = CliRunner()
    runner.invoke(commands.main, ("routes", 'salmon.handlers.log', 'salmon.handlers.queue'))

    # test with the --test option
    runner.invoke(commands.main, ("routes", 'salmon.handlers.log', 'salmon.handlers.queue',
                                  "--test", "anything@localhost"))

    # test with the -test option but no matches
    routing.Router.clear_routes()
    runner.invoke(commands.main, ("routes", "--test", "anything@localhost"))


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
@patch('salmon.utils.daemonize', new=Mock())
@patch('salmon.server.SMTPReceiver')
def test_log_command(MockSMTPReceiver):
    runner = CliRunner()
    ms = MockSMTPReceiver()
    ms.start.function()

    setup()  # make sure it's clear for fake.pid
    result = runner.invoke(commands.main, ("log", "--host", "127.0.0.1", "--port", "8825", "--pid", "run/fake.pid"))
    assert_equal(utils.daemonize.call_count, 1)
    assert_equal(ms.start.call_count, 1)
    assert_equal(result.exit_code, 0)

    # test that it exits on existing pid
    make_fake_pid_file()
    result = runner.invoke(commands.main, ("log", "--host", "127.0.0.1", "--port", "8825", "--pid", "run/fake.pid"))
    assert_equal(result.exit_code, 1)


@patch('sys.stdin', new=Mock())
@patch("salmon.server.smtplib.SMTP")
def test_sendmail_command(client_mock):
    sys.stdin.read.function()

    msg = mail.MailResponse(To="tests@localhost", From="tests@localhost",
                            Subject="Hello", Body="Test body.")
    sys.stdin.read.return_value = str(msg)

    runner = CliRunner()
    runner.invoke(commands.main, ("sendmail", "--host", "127.0.0.1", "--port", "8899", "test@localhost"))
    assert_equal(client_mock.return_value.sendmail.call_count, 1)


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
@patch('salmon.utils.daemonize', new=Mock())
@patch('salmon.utils.import_settings', new=Mock())
@patch('salmon.utils.drop_priv', new=Mock())
@patch('sys.path', new=Mock())
def test_start_command():
    # normal start
    runner = CliRunner()
    runner.invoke(commands.main, ("start", "--pid", "smtp.pid"))
    assert_equal(utils.daemonize.call_count, 1)
    assert_equal(utils.import_settings.call_count, 1)

    # start with pid file existing already
    make_fake_pid_file()
    result = runner.invoke(commands.main, ("start", "--pid", "run/fake.pid"))
    assert_equal(result.exit_code, 1)

    # start with pid file existing and force given
    assert os.path.exists("run/fake.pid")
    runner.invoke(commands.main, ("start", "--force", "--pid", "run/fake.pid"))
    assert not os.path.exists("run/fake.pid")

    # start with a uid but no gid
    runner.invoke(commands.main, ("start", "--uid", "1000", "--pid", "run/fake.pid", "--force"))
    assert_equal(utils.drop_priv.call_count, 0)

    # start with a uid/gid given that's valid
    runner.invoke(commands.main, ("start", "--uid", "1000", "--gid", "1000", "--pid", "run/fake.pid", "--force"))
    assert_equal(utils.drop_priv.call_count, 1)

    # non daemon start
    daemonize_call_count = utils.daemonize.call_count
    runner.invoke(commands.main, ("start", "--pid", "run/fake.pid", "--no-daemon", "--force"))
    assert_equal(utils.daemonize.call_count, daemonize_call_count)  # same count -> not called


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
@patch('os.kill', new=Mock())
@patch('glob.glob', new=lambda x: ['run/fake.pid'])
def test_stop_command():
    runner = CliRunner()
    # gave a bad pid file
    result = runner.invoke(commands.main, ("stop", "--pid", "run/dontexit.pid"))
    assert_equal(result.exit_code, 1)

    make_fake_pid_file()
    runner.invoke(commands.main, ("stop", "--pid", "run/fake.pid"))

    make_fake_pid_file()
    runner.invoke(commands.main, ("stop", "--all", "run"))

    os_kill_count = os.kill.call_count
    make_fake_pid_file()
    runner.invoke(commands.main, ("stop", "--pid", "run/fake.pid", "--force"))
    assert_equal(os.kill.call_count, os_kill_count + 1)  # kill should have been called once more
    assert not os.path.exists("run/fake.pid")

    make_fake_pid_file()
    os.kill.side_effect = OSError("Fail")
    runner.invoke(commands.main, ("stop", "--pid", "run/fake.pid", "--force"))


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
def test_cleanse_command():
    runner = CliRunner()
    runner.invoke(commands.main, ("cleanse", "run/queue", "run/cleansed"))
    assert os.path.exists('run/cleansed')


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
@patch('salmon.encoding.from_message')
def test_cleans_command_with_encoding_error(from_message):
    runner = CliRunner()
    from_message.side_effect = encoding.EncodingError

    runner.invoke(commands.main, ("cleanse", "run/queue", "run/cleased"))


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
def test_blast_command():
    runner = CliRunner()
    runner.invoke(commands.main, ("blast", "--host", "127.0.0.1", "--port", "8899", "run/queue"))
