import sys

from mock import Mock

from salmon import mail, utils
from salmon.routing import Router

from .setup_env import SalmonTestCase

sample_message = """From: someone@localhost
To: someone@localhost

Test
"""


def create_message():
    return mail.MailRequest("localhost", "someone@localhost", "someone@localhost", sample_message)


class HandlerTestCase(SalmonTestCase):
    def tearDown(self):
        Router.clear_routes()
        Router.clear_states()
        for key in Router.HANDLERS.keys():
            del sys.modules[key]
        Router.HANDLERS.clear()
        utils.settings = None

    def test_log_handler(self):
        import salmon.handlers.log  # noqa
        Router.deliver(create_message())

    def test_queue_handler(self):
        import salmon.handlers.queue  # noqa
        Router.deliver(create_message())

    def test_forward(self):
        utils.import_settings(False)

        import salmon.handlers.forward  # noqa
        salmon.handlers.forward.settings.relay = Mock()
        Router.deliver(create_message())

        self.assertEqual(salmon.handlers.forward.settings.relay.deliver.call_count, 1)
