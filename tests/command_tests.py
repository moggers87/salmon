import os
import shutil
import sys

from click import testing
from mock import Mock, patch

from salmon import commands, encoding, mail, routing, utils

from .setup_env import SalmonTestCase


def make_fake_pid_file():
    with open("run/fake.pid", "w") as f:
        f.write("0")


class CliRunner(testing.CliRunner):
    def invoke(self, *args, **kwargs):
        kwargs.setdefault("catch_exceptions", False)
        return super(CliRunner, self).invoke(*args, **kwargs)


class CommandTestCase(SalmonTestCase):
    @patch("salmon.server.smtplib.SMTP")
    def test_send_command(self, client_mock):
        runner = CliRunner()
        runner.invoke(commands.main, ("send", "--sender", "test@localhost", "--to", "test@localhost",
                                      "--body", "Test body", "--subject", "Test subject", "--attach",
                                      "setup.py", "--port", "8899", "--host", "127.0.0.1"))
        self.assertEqual(client_mock.return_value.sendmail.call_count, 1)

    def test_status_command(self):
        make_fake_pid_file()
        runner = CliRunner()
        running_result = runner.invoke(commands.main, ("status", "--pid", 'run/fake.pid'))
        self.assertEqual(running_result.output, "Salmon running with PID 0\n")
        not_running_result = runner.invoke(commands.main, ("status", "--pid", 'run/donotexist.pid'))
        self.assertEqual(not_running_result.output, "Salmon not running.\n")

    def test_main(self):
        runner = CliRunner()
        runner.invoke(commands.main)

    @patch('salmon.queue.Queue')
    def test_queue_command(self, MockQueue):
        mq = MockQueue()
        mq.get.return_value = "A sample message"
        mq.keys.return_value = ["key1", "key2"]
        mq.pop.return_value = ('key1', 'message1')
        mq.count.return_value = 1

        runner = CliRunner()

        runner.invoke(commands.main, ("queue", "--pop"))
        self.assertEqual(mq.pop.call_count, 1)

        runner.invoke(commands.main, ("queue", "--get", "somekey"))
        self.assertEqual(mq.get.call_count, 1)

        runner.invoke(commands.main, ("queue", "--remove", "somekey"))
        self.assertEqual(mq.remove.call_count, 1)

        runner.invoke(commands.main, ("queue", "--clear"))
        self.assertEqual(mq.clear.call_count, 1)

        runner.invoke(commands.main, ("queue", "--keys"))
        self.assertEqual(mq.keys.call_count, 1)

        runner.invoke(commands.main, ("queue", "--count"))
        self.assertEqual(mq.count.call_count, 1)

    def test_gen_command(self):
        runner = CliRunner()
        project = 'tests/testproject'
        if os.path.exists(project):
            shutil.rmtree(project)

        result = runner.invoke(commands.main, ("gen", project))
        assert os.path.exists(project)
        self.assertEqual(result.exit_code, 0)

        # test that it exits if the project exists
        result = runner.invoke(commands.main, ("gen", project))
        self.assertEqual(result.exit_code, 1)

        result = runner.invoke(commands.main, ("gen", project, "--force"))
        self.assertEqual(result.exit_code, 0)

        # TODO: put this in a tear down
        shutil.rmtree(project)

    def test_routes_command(self):
        runner = CliRunner()
        runner.invoke(commands.main, ("routes", 'salmon.handlers.log', 'salmon.handlers.queue'))

        # test with the --test option
        runner.invoke(commands.main, ("routes", 'salmon.handlers.log', 'salmon.handlers.queue',
                                      "--test", "anything@localhost"))

        # test with the -test option but no matches
        routing.Router.clear_routes()
        runner.invoke(commands.main, ("routes", "--test", "anything@localhost"))

    @patch('salmon.utils.daemonize', new=Mock())
    @patch('salmon.server.SMTPReceiver')
    def test_log_command(self, MockSMTPReceiver):
        runner = CliRunner()
        ms = MockSMTPReceiver()
        ms.start.function()

        result = runner.invoke(commands.main, ("log", "--host", "127.0.0.1", "--port", "8825", "--pid", "run/fake.pid"))
        self.assertEqual(utils.daemonize.call_count, 1)
        self.assertEqual(ms.start.call_count, 1)
        self.assertEqual(result.exit_code, 0)

        # test that it exits on existing pid
        make_fake_pid_file()
        result = runner.invoke(commands.main, ("log", "--host", "127.0.0.1", "--port", "8825", "--pid", "run/fake.pid"))
        self.assertEqual(result.exit_code, 1)

    @patch('sys.stdin', new=Mock())
    @patch("salmon.server.smtplib.SMTP")
    def test_sendmail_command(self, client_mock):
        sys.stdin.read.function()

        msg = mail.MailResponse(To="tests@localhost", From="tests@localhost",
                                Subject="Hello", Body="Test body.")
        sys.stdin.read.return_value = str(msg)

        runner = CliRunner()
        runner.invoke(commands.main, ("sendmail", "--host", "127.0.0.1", "--port", "8899", "test@localhost"))
        self.assertEqual(client_mock.return_value.sendmail.call_count, 1)

    @patch('salmon.utils.daemonize', new=Mock())
    @patch('salmon.utils.import_settings', new=Mock())
    @patch('salmon.utils.drop_priv', new=Mock())
    @patch('sys.path', new=Mock())
    def test_start_command(self):
        # normal start
        runner = CliRunner()
        runner.invoke(commands.main, ("start", "--pid", "smtp.pid"))
        self.assertEqual(utils.daemonize.call_count, 1)
        self.assertEqual(utils.import_settings.call_count, 1)

        # start with pid file existing already
        make_fake_pid_file()
        result = runner.invoke(commands.main, ("start", "--pid", "run/fake.pid"))
        self.assertEqual(result.exit_code, 1)

        # start with pid file existing and force given
        assert os.path.exists("run/fake.pid")
        runner.invoke(commands.main, ("start", "--force", "--pid", "run/fake.pid"))
        assert not os.path.exists("run/fake.pid")

        # start with a uid but no gid
        runner.invoke(commands.main, ("start", "--uid", "1000", "--pid", "run/fake.pid", "--force"))
        self.assertEqual(utils.drop_priv.call_count, 0)

        # start with a uid/gid given that's valid
        runner.invoke(commands.main, ("start", "--uid", "1000", "--gid", "1000", "--pid", "run/fake.pid", "--force"))
        self.assertEqual(utils.drop_priv.call_count, 1)

        # non daemon start
        daemonize_call_count = utils.daemonize.call_count
        runner.invoke(commands.main, ("start", "--pid", "run/fake.pid", "--no-daemon", "--force"))
        self.assertEqual(utils.daemonize.call_count, daemonize_call_count)  # same count -> not called

    @patch('os.kill', new=Mock())
    @patch('glob.glob', new=lambda x: ['run/fake.pid'])
    def test_stop_command(self):
        runner = CliRunner()
        # gave a bad pid file
        result = runner.invoke(commands.main, ("stop", "--pid", "run/dontexit.pid"))
        self.assertEqual(result.exit_code, 1)

        make_fake_pid_file()
        runner.invoke(commands.main, ("stop", "--pid", "run/fake.pid"))

        make_fake_pid_file()
        runner.invoke(commands.main, ("stop", "--all", "run"))

        os_kill_count = os.kill.call_count
        make_fake_pid_file()
        runner.invoke(commands.main, ("stop", "--pid", "run/fake.pid", "--force"))
        self.assertEqual(os.kill.call_count, os_kill_count + 1)  # kill should have been called once more
        assert not os.path.exists("run/fake.pid")

        make_fake_pid_file()
        os.kill.side_effect = OSError("Fail")
        runner.invoke(commands.main, ("stop", "--pid", "run/fake.pid", "--force"))

    def test_cleanse_command(self):
        runner = CliRunner()
        runner.invoke(commands.main, ("cleanse", "run/queue", "run/cleansed"))
        assert os.path.exists('run/cleansed')

    @patch('salmon.encoding.from_message')
    def test_cleans_command_with_encoding_error(self, from_message):
        runner = CliRunner()
        from_message.side_effect = encoding.EncodingError

        runner.invoke(commands.main, ("cleanse", "run/queue", "run/cleased"))

    def test_blast_command(self):
        runner = CliRunner()
        runner.invoke(commands.main, ("blast", "--host", "127.0.0.1", "--port", "8899", "run/queue"))
