from mock import patch
from nose.tools import assert_equal, with_setup

from salmon import utils

from .setup_env import setup_salmon_dirs, teardown_salmon_dirs


def clear_settings():
    utils.settings = None


@with_setup(teardown=clear_settings)
def test_make_fake_settings():
    settings = utils.make_fake_settings('localhost', 8800)
    assert settings
    assert settings.receiver
    assert settings.relay is None
    settings.receiver.close()


@with_setup(teardown=clear_settings)
def test_import_settings():
    assert utils.settings is None

    settings = utils.import_settings(True, boot_module='config.testing')
    assert settings
    assert settings.receiver_config
    assert_equal(settings, utils.settings)

    with patch("salmon.utils.importlib.import_module") as import_mock:
        # just import settings module
        clear_settings()
        utils.import_settings(False)
        assert_equal(import_mock.call_count, 1)

        # import settings and boot
        clear_settings()
        import_mock.reset_mock()
        utils.import_settings(True)
        assert_equal(import_mock.call_count, 2)

        # settings has already been imported, return early
        import_mock.reset_mock()
        utils.import_settings(False)
        assert_equal(import_mock.call_count, 0)

        # boot module doesn't get cached on the module, so it import_module should be called
        import_mock.reset_mock()
        utils.import_settings(True)
        assert_equal(import_mock.call_count, 1)


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
@patch('daemon.DaemonContext.open')
def test_daemonize_not_fully(dc_open):
    context = utils.daemonize("run/tests.pid", ".", False, False, do_open=False)
    assert context
    assert_equal(dc_open.call_count, 0)
    dc_open.reset_mock()

    context = utils.daemonize("run/tests.pid", ".", "/tmp", 0o002, do_open=True)
    assert context
    assert_equal(dc_open.call_count, 1)


@patch("daemon.daemon.change_process_owner")
def test_drop_priv(cpo):
    utils.drop_priv(100, 100)
    assert_equal(cpo.call_count, 1)
