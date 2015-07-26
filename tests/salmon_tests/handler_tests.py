from salmon.routing import Router
from salmon_tests import message_tests


def test_log_handler():
    import salmon.handlers.log  # noqa
    Router.deliver(message_tests.test_mail_request())


def test_queue_handler():
    import salmon.handlers.queue  # noqa
    Router.deliver(message_tests.test_mail_request())
