from mock import patch

from salmon import utils

from .setup_env import SalmonTestCase


class UtilsTestCase(SalmonTestCase):
    def tearDown(self):
        super(UtilsTestCase, self).tearDown()
        self.clear_settings()

    def clear_settings(self):
        utils.settings = None

    def test_make_fake_settings(self):
        settings = utils.make_fake_settings('localhost', 8800)
        assert settings
        assert settings.receiver
        assert settings.relay is None
        settings.receiver.close()

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

    @patch('daemon.DaemonContext.open')
    def test_daemonize_not_fully(self, dc_open):
        context = utils.daemonize("run/tests.pid", ".", False, False, do_open=False)
        assert context
        self.assertEqual(dc_open.call_count, 0)
        dc_open.reset_mock()

        context = utils.daemonize("run/tests.pid", ".", "/tmp", 0o002, do_open=True)
        assert context
        self.assertEqual(dc_open.call_count, 1)

    @patch("daemon.daemon.change_process_owner")
    def test_drop_priv(self, cpo):
        utils.drop_priv(100, 100)
        self.assertEqual(cpo.call_count, 1)
