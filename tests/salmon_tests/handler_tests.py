from mock import Mock, patch
from nose.tools import with_setup

from salmon import mail, utils
from salmon.routing import Router


sample_message = """From: someone@localhost
To: someone@localhost

Test
"""


def create_message():
    return mail.MailRequest("localhost", "someone@localhost", "someone@localhost", sample_message)


def cleanup_router():
    Router.clear_routes()
    Router.clear_states()
    Router.HANDLERS.clear()
    utils.settings = None


@with_setup(teardown=cleanup_router)
def test_log_handler():
    import salmon.handlers.log  # noqa
    Router.deliver(create_message())


@with_setup(teardown=cleanup_router)
def test_queue_handler():
    import salmon.handlers.queue  # noqa
    Router.deliver(create_message())


@patch("smtplib.SMTP")
@with_setup(teardown=cleanup_router)
def test_forward(smtp_mock):
    smtp_mock.return_value = Mock()

    utils.import_settings(False)

    import salmon.handlers.forward  # noqa
    Router.deliver(create_message())

    assert smtp_mock.return_value.sendmail.called
    assert smtp_mock.return_value.quit.called
