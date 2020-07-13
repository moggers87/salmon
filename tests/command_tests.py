from tempfile import mkdtemp
from unittest.mock import Mock, patch
import mailbox
import os
import sys

from click import testing

from salmon import queue, commands, encoding, mail, routing, utils

from .setup_env import SalmonTestCase


def make_fake_pid_file():
    with open("run/fake.pid", "w") as f:
        f.write("0")


class CliRunner(testing.CliRunner):
    def invoke(self, *args, **kwargs):
        kwargs.setdefault("catch_exceptions", False)
        return super().invoke(*args, **kwargs)


class CommandTestCase(SalmonTestCase):
    @patch("salmon.server.smtplib.SMTP")
    def test_send_command(self, client_mock):
        runner = CliRunner()
        result = runner.invoke(commands.main, ("send", "--sender", "test@localhost", "--to", "test@localhost",
                                               "--body", "Test body", "--subject", "Test subject", "--attach",
                                               "setup.py", "--port", "8899", "--host", "127.0.0.1"))
        self.assertEqual(client_mock.return_value.sendmail.call_count, 1)
        self.assertEqual(result.exit_code, 0)

    def test_status_command(self):
        make_fake_pid_file()
        runner = CliRunner()
        running_result = runner.invoke(commands.main, ("status", "--pid", 'run/fake.pid'))
        self.assertEqual(running_result.output, "Salmon running with PID 0\n")
        self.assertEqual(running_result.exit_code, 0)

    def test_status_no_pid(self):
        runner = CliRunner()
        not_running_result = runner.invoke(commands.main, ("status", "--pid", 'run/donotexist.pid'))
        self.assertEqual(not_running_result.output, "Salmon not running.\n")
        self.assertEqual(not_running_result.exit_code, 1)

    def test_main(self):
        runner = CliRunner()
        result = runner.invoke(commands.main)
        self.assertEqual(result.exit_code, 0)

    @patch('salmon.queue.Queue')
    def test_queue_command(self, MockQueue):
        mq = MockQueue()
        mq.get.return_value = "A sample message"
        mq.keys.return_value = ["key1", "key2"]
        mq.pop.return_value = ('key1', 'message1')
        mq.__len__.return_value = 1

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
        self.assertEqual(mq.__len__.call_count, 1)

    @patch('salmon.utils.daemonize')
    @patch('salmon.server.AsyncSMTPReceiver')
    def test_log_command(self, MockSMTPReceiver, daemon_mock):
        runner = CliRunner()
        ms = MockSMTPReceiver()
        ms.start.function()

        result = runner.invoke(commands.main, ("log", "--host", "127.0.0.1", "--port", "8825", "--pid", "run/fake.pid"))
        self.assertEqual(daemon_mock.call_count, 1)
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


class StartCommandTestCase(SalmonTestCase):
    @patch('salmon.utils.daemonize')
    @patch('salmon.utils.import_settings')
    @patch('salmon.utils.drop_priv')
    def test_start_command(self, priv_mock, settings_mock, daemon_mock):
        runner = CliRunner()
        runner.invoke(commands.main, ("start", "--pid", "smtp.pid"))
        self.assertEqual(daemon_mock.call_count, 1)
        self.assertEqual(daemon_mock.call_args, (("smtp.pid", ".", None, None), {"files_preserve": []}))
        self.assertEqual(settings_mock.call_count, 1)
        self.assertEqual(settings_mock.call_args, ((True,), {"boot_module": "config.boot"}))

    @patch('salmon.utils.daemonize')
    @patch('salmon.utils.import_settings')
    def test_pid(self, settings_mock, daemon_mock):
        runner = CliRunner()
        # start with pid file existing already
        make_fake_pid_file()
        result = runner.invoke(commands.main, ("start", "--pid", "run/fake.pid"))
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(daemon_mock.call_count, 0)

        # start with pid file existing and force given
        self.assertTrue(os.path.exists("run/fake.pid"))
        runner.invoke(commands.main, ("start", "--force", "--pid", "run/fake.pid"))
        self.assertFalse(os.path.exists("run/fake.pid"))
        self.assertEqual(daemon_mock.call_count, 1)
        self.assertEqual(daemon_mock.call_args, (("run/fake.pid", ".", None, None), {"files_preserve": []}))

    @patch('salmon.utils.daemonize')
    @patch('salmon.utils.import_settings')
    @patch('salmon.utils.drop_priv')
    def test_set_uid_and_guid(self, priv_mock, settings_mock, daemon_mock):
        runner = CliRunner()
        # start with a uid but no gid
        runner.invoke(commands.main, ("start", "--uid", "1000", "--pid", "run/fake.pid", "--force"))
        self.assertEqual(priv_mock.call_count, 0)
        self.assertEqual(daemon_mock.call_count, 1)
        self.assertEqual(daemon_mock.call_args, (("run/fake.pid", ".", None, None), {"files_preserve": []}))

        # start with a uid/gid given that's valid
        runner.invoke(commands.main, ("start", "--uid", "1000", "--gid", "1000", "--pid", "run/fake.pid", "--force"))
        self.assertEqual(priv_mock.call_count, 1)
        self.assertEqual(priv_mock.call_args, ((1000, 1000), {}))
        self.assertEqual(daemon_mock.call_count, 2)
        self.assertEqual(daemon_mock.call_args, (("run/fake.pid", ".", None, None), {"files_preserve": []}))

    @patch('salmon.utils.daemonize')
    @patch('salmon.utils.import_settings')
    def test_non_daemon(self, settings_mock, daemon_mock):
        runner = CliRunner()
        runner.invoke(commands.main, ("start", "--pid", "run/fake.pid", "--no-daemon", "--force"))
        self.assertEqual(daemon_mock.call_count, 0)


class CleanseCommandTestCase(SalmonTestCase):
    def setUp(self):
        super().setUp()
        queue.Queue("run/queue").clear()

    def test_cleanse_command(self):
        q = queue.Queue("run/queue")
        msg_count = 3
        for i in range(msg_count):
            msg = mail.MailResponse(To="tests%s@localhost" % i, From="tests%s@localhost" % i,
                                    Subject="Hello", Body="Test body.")
            q.push(msg)
        self.assertEqual(q.count(), msg_count)
        runner = CliRunner()
        result = runner.invoke(commands.main, ("cleanse", "run/queue", "run/cleansed"))
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(q.count(), msg_count)
        outbox = mailbox.Maildir("run/cleansed", create=False)
        self.assertEqual(len(outbox), msg_count)

    def test_no_inbox(self):
        runner = CliRunner()
        result = runner.invoke(commands.main, ("cleanse", "run/not-a-queue", "run/cleansed"))
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.output, "Error: run/not-a-queue does not exist or is not a valid MBox or Maildir\n")
        self.assertFalse(os.path.exists('run/cleansed'))

    def test_empty(self):
        runner = CliRunner()
        result = runner.invoke(commands.main, ("cleanse", "run/queue", "run/cleansed"))
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(os.path.exists('run/cleansed'))

    @patch('salmon.encoding.from_message')
    def test_encoding_error(self, from_message):
        runner = CliRunner()
        from_message.side_effect = encoding.EncodingError
        in_queue = "run/queue"
        q = queue.Queue(in_queue)
        q.push("hello")

        result = runner.invoke(commands.main, ("cleanse", in_queue, "run/cleased"))
        self.assertEqual(result.exit_code, 1)


class GenCommandTestCase(SalmonTestCase):
    def setUp(self):
        super().setUp()
        tmp_dir = mkdtemp()
        self.project = os.path.join(tmp_dir, 'testproject')

    def test_gen_command(self):
        runner = CliRunner()

        result = runner.invoke(commands.main, ("gen", self.project))
        assert os.path.exists(self.project)
        self.assertEqual(result.exit_code, 0)

    def test_if_folder_exists(self):
        runner = CliRunner()
        os.mkdir(self.project)

        result = runner.invoke(commands.main, ("gen", self.project))
        self.assertEqual(result.exit_code, 1)

    def test_force(self):
        runner = CliRunner()

        # folder doesn't exist, but user has used --force anyway
        result = runner.invoke(commands.main, ("gen", self.project, "--force"))
        assert os.path.exists(self.project)
        self.assertEqual(result.exit_code, 0)

        # assert again, this time the folder exists
        result = runner.invoke(commands.main, ("gen", self.project, "--force"))
        assert os.path.exists(self.project)
        self.assertEqual(result.exit_code, 0)


class StopCommandTestCase(SalmonTestCase):
    def setUp(self):
        super().setUp()
        patcher = patch("os.kill")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_stop_command(self):
        runner = CliRunner()
        make_fake_pid_file()
        result = runner.invoke(commands.main, ("stop", "--pid", "run/fake.pid"))
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(os.kill.call_count, 1)

    def test_stop_pid_doesnt_exist(self):
        runner = CliRunner()
        result = runner.invoke(commands.main, ("stop", "--pid", "run/dontexit.pid"))
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(os.kill.call_count, 0)

    @patch('glob.glob', new=lambda x: ['run/fake.pid'])
    def test_stop_all(self):
        runner = CliRunner()
        make_fake_pid_file()
        result = runner.invoke(commands.main, ("stop", "--all", "run"))
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(os.kill.call_count, 1)

    def test_stop_force(self):
        runner = CliRunner()
        make_fake_pid_file()
        result = runner.invoke(commands.main, ("stop", "--pid", "run/fake.pid", "--force"))
        self.assertEqual(os.kill.call_count, 1)
        self.assertEqual(result.exit_code, 0)
        assert not os.path.exists("run/fake.pid")

    def test_stop_force_oserror(self):
        runner = CliRunner()
        make_fake_pid_file()
        os.kill.side_effect = OSError("Fail")
        result = runner.invoke(commands.main, ("stop", "--pid", "run/fake.pid", "--force"))
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(os.kill.call_count, 1)


class RoutesCommandTestCase(SalmonTestCase):
    def setUp(self):
        super().setUp()
        if "salmon.handlers.log" in sys.modules:
            del sys.modules["salmon.handlers.log"]
        routing.Router.clear_routes()
        routing.Router.clear_states()
        routing.Router.HANDLERS.clear()
        utils.settings = None

    def test_no_args(self):
        runner = CliRunner()
        result = runner.invoke(commands.main, ("routes",))
        self.assertEqual(result.exit_code, 2)

    def test_not_importable(self):
        runner = CliRunner()
        result = runner.invoke(commands.main, ("routes", "not_a_module", "--test", "user@example.com"))
        self.assertEqual(result.exit_code, 1)
        self.assertIsNotNone(utils.settings)
        self.assertEqual(result.output,
                         ("Error: Module 'not_a_module' could not be imported. "
                          "Did you forget to use the --path option?\n"))

    def test_match(self):
        runner = CliRunner()
        result = runner.invoke(commands.main, ("routes", "salmon.handlers.log", "--test", "user@example.com"))
        self.assertEqual(result.exit_code, 0)
        self.assertIsNotNone(utils.settings)
        match_items = list(routing.Router.REGISTERED.values())[0][0].match("user@example.com").groupdict()
        self.assertEqual(result.output,
                         ("Routing ORDER: ['^(?P<to>.+)@(?P<host>.+)$']\n"
                          "Routing TABLE:\n"
                          "---\n"
                          "'^(?P<to>.+)@(?P<host>.+)$': salmon.handlers.log.START \n"
                          "---\n"
                          "\n"
                          "TEST address 'user@example.com' matches:\n"
                          "  '^(?P<to>.+)@(?P<host>.+)$' salmon.handlers.log.START\n"
                          "  -  %r\n" % match_items))

    def test_no_match(self):
        runner = CliRunner()
        result = runner.invoke(commands.main, ("routes", "salmon.handlers.log", "--test", "userexample.com"))
        self.assertEqual(result.exit_code, 1)
        self.assertIsNotNone(utils.settings)
        self.assertEqual(result.output,
                         ("Routing ORDER: ['^(?P<to>.+)@(?P<host>.+)$']\n"
                          "Routing TABLE:\n"
                          "---\n"
                          "'^(?P<to>.+)@(?P<host>.+)$': salmon.handlers.log.START \n"
                          "---\n"
                          "\n"
                          "TEST address 'userexample.com' didn't match anything.\n"))

    def test_no_test(self):
        runner = CliRunner()
        result = runner.invoke(commands.main, ("routes", "salmon.handlers.log"))
        self.assertEqual(result.exit_code, 0)
        self.assertIsNotNone(utils.settings)
        self.assertEqual(result.output,
                         ("Routing ORDER: ['^(?P<to>.+)@(?P<host>.+)$']\n"
                          "Routing TABLE:\n"
                          "---\n"
                          "'^(?P<to>.+)@(?P<host>.+)$': salmon.handlers.log.START \n"
                          "---\n"))


class BlastCommandTestCase(SalmonTestCase):
    def setUp(self):
        super().setUp()
        queue.Queue("run/queue").clear()

    @patch("salmon.server.smtplib.SMTP")
    def test_blast_command_empty(self, client_mock):
        runner = CliRunner()
        result = runner.invoke(commands.main, ("blast", "--host", "129.0.0.1", "--port", "8899", "run/queue"))
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(client_mock.call_count, 0)
        self.assertEqual(client_mock.return_value.sendmail.call_count, 0)

    @patch("salmon.server.smtplib.SMTP")
    def test_blast_three_messages(self, client_mock):
        q = queue.Queue("run/queue")
        msg_count = 3
        for i in range(msg_count):
            msg = mail.MailResponse(To="tests%s@localhost" % i, From="tests%s@localhost" % i,
                                    Subject="Hello", Body="Test body.")
            q.push(msg)
        runner = CliRunner()
        result = runner.invoke(commands.main, ("blast", "--host", "127.0.0.2", "--port", "8900", "run/queue"))
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(client_mock.call_count, msg_count)
        self.assertEqual(client_mock.call_args_list, [
            (("127.0.0.2", 8900), {}),
            (("127.0.0.2", 8900), {}),
            (("127.0.0.2", 8900), {}),
        ])
        self.assertEqual(client_mock.return_value.sendmail.call_count, msg_count)

    def test_no_connection(self):
        q = queue.Queue("run/queue")
        msg = mail.MailResponse(To="tests@localhost", From="tests@localhost",
                                Subject="Hello", Body="Test body.")
        q.push(msg)
        runner = CliRunner()
        result = runner.invoke(commands.main, ("blast", "--host", "127.0.1.2", "--port", "8901", "run/queue"))
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.output, "Error: [Errno 111] Connection refused\n")

    def test_no_queue(self):
        runner = CliRunner()
        result = runner.invoke(commands.main, ("blast", "--host", "127.1.1.2", "--port", "8889", "run/not-a-queue"))
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.output, "Error: run/not-a-queue does not exist or is not a valid MBox or Maildir\n")
