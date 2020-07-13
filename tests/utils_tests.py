from tempfile import mkdtemp
from unittest import TestCase
from unittest.mock import patch
import os

from salmon import utils

from .setup_env import SalmonTestCase


class UtilsTestCase(SalmonTestCase):
    def tearDown(self):
        super().tearDown()
        self.clear_settings()

    def clear_settings(self):
        utils.settings = None

    def test_make_fake_settings(self):
        settings = utils.make_fake_settings('localhost', 8800)
        assert settings
        assert settings.receiver
        assert settings.relay is None

    def test_import_settings(self):
        assert utils.settings is None

        settings = utils.import_settings(True, boot_module='config.testing')
        assert settings
        assert settings.receiver_config
        self.assertEqual(settings, utils.settings)

        with patch("salmon.utils.importlib.import_module") as import_mock:
            # just import settings module
            self.clear_settings()
            utils.import_settings(False)
            self.assertEqual(import_mock.call_count, 1)

            # import settings and boot
            self.clear_settings()
            import_mock.reset_mock()
            utils.import_settings(True)
            self.assertEqual(import_mock.call_count, 2)

            # settings has already been imported, return early
            import_mock.reset_mock()
            utils.import_settings(False)
            self.assertEqual(import_mock.call_count, 0)

            # boot module doesn't get cached on the module, so it import_module should be called
            import_mock.reset_mock()
            utils.import_settings(True)
            self.assertEqual(import_mock.call_count, 1)

    @patch("daemon.daemon.change_process_owner")
    def test_drop_priv(self, cpo):
        utils.drop_priv(100, 100)
        self.assertEqual(cpo.call_count, 1)
        self.assertEqual(cpo.call_args, ((100, 100), {}))


@patch('daemon.DaemonContext.open')
class DaemonizeTestCase(TestCase):
    def setUp(self):
        self.tmp_dir = mkdtemp()

    def error_maybe(self, check, fn):
        def maybe(*args, **kwargs):
            if check(*args, **kwargs):
                raise AssertionError("function called on {} {}".format(args, kwargs))
            else:
                fn(*args, **kwargs)

        return maybe

    def test_working_dir(self, dc_open):
        context = utils.daemonize("run/tests.pid", self.tmp_dir, None, None, do_open=False)
        self.assertEqual(dc_open.call_count, 0)
        self.assertEqual(context.working_directory, self.tmp_dir)
        self.assertEqual(context.chroot_directory, None)
        self.assertEqual(context.stdout.name, os.path.join(self.tmp_dir, "logs", "salmon.out"))
        self.assertEqual(context.stderr.name, os.path.join(self.tmp_dir, "logs", "salmon.err"))
        self.assertEqual(context.pidfile.path, os.path.join("run", "tests.pid"))
        self.assertEqual(context.umask, 0)

    def test_open_is_called(self, dc_open):
        context = utils.daemonize("run/tests.pid", self.tmp_dir, None, None, do_open=True)
        self.assertEqual(dc_open.call_count, 1)
        self.assertEqual(context.chroot_directory, None)
        self.assertEqual(context.stdout.name, os.path.join(self.tmp_dir, "logs", "salmon.out"))
        self.assertEqual(context.stderr.name, os.path.join(self.tmp_dir, "logs", "salmon.err"))
        self.assertEqual(context.pidfile.path, os.path.join("run", "tests.pid"))
        self.assertEqual(context.umask, 0)

    def test_chroot(self, dc_open):
        context = utils.daemonize("run/tests.pid", ".", self.tmp_dir, None, do_open=False)
        self.assertEqual(dc_open.call_count, 0)
        self.assertEqual(context.working_directory, ".")
        self.assertEqual(context.chroot_directory, self.tmp_dir)
        self.assertEqual(context.stdout.name, os.path.join(self.tmp_dir, ".", "logs", "salmon.out"))
        self.assertEqual(context.stderr.name, os.path.join(self.tmp_dir, ".", "logs", "salmon.err"))
        self.assertEqual(context.pidfile.path, os.path.join("run", "tests.pid"))
        self.assertEqual(context.umask, 0)

    def test_pid_dir_already_exists(self, dc_open):
        os.mkdir(os.path.join(self.tmp_dir, "run"))
        with patch("os.mkdir", self.error_maybe(lambda p: p.endswith("/run"), os.mkdir)):
            context = utils.daemonize("run/tests.pid", self.tmp_dir, None, None, do_open=False)
        self.assertEqual(dc_open.call_count, 0)
        self.assertEqual(context.working_directory, self.tmp_dir)
        self.assertEqual(context.stdout.name, os.path.join(self.tmp_dir, "logs", "salmon.out"))
        self.assertEqual(context.stderr.name, os.path.join(self.tmp_dir, "logs", "salmon.err"))
        self.assertEqual(context.pidfile.path, os.path.join("run", "tests.pid"))
        self.assertEqual(context.umask, 0)

    def test_logs_dir_already_exists(self, dc_open):
        os.mkdir(os.path.join(self.tmp_dir, "logs"))
        with patch("os.mkdir", self.error_maybe(lambda p: p.endswith("/logs"), os.mkdir)):
            context = utils.daemonize("run/tests.pid", self.tmp_dir, None, None, do_open=False)
        self.assertEqual(dc_open.call_count, 0)
        self.assertEqual(context.working_directory, self.tmp_dir)
        self.assertEqual(context.stdout.name, os.path.join(self.tmp_dir, "logs", "salmon.out"))
        self.assertEqual(context.stderr.name, os.path.join(self.tmp_dir, "logs", "salmon.err"))
        self.assertEqual(context.pidfile.path, os.path.join("run", "tests.pid"))
        self.assertEqual(context.umask, 0)

    def test_chdir_does_not_exist(self, dc_open):
        chdir = os.path.join(self.tmp_dir, "test")
        with self.assertRaises(OSError):
            utils.daemonize("run/tests.pid", chdir, None, None, do_open=False)
        self.assertEqual(dc_open.call_count, 0)

    def test_umask(self, dc_open):
        context = utils.daemonize("run/tests.pid", self.tmp_dir, None, 0o002, do_open=False)
        self.assertEqual(context.chroot_directory, None)
        self.assertEqual(context.stdout.name, os.path.join(self.tmp_dir, "logs", "salmon.out"))
        self.assertEqual(context.stderr.name, os.path.join(self.tmp_dir, "logs", "salmon.err"))
        self.assertEqual(context.pidfile.path, os.path.join("run", "tests.pid"))
        self.assertEqual(context.umask, 2)
