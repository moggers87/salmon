from mock import Mock, patch

from salmon.testing import RouterConversation, assert_in_state, clear_queue, delivered, queue, relay

from .setup_env import SalmonTestCase


class TestingTestCase(SalmonTestCase):
    def test_clear_queue(self):
        queue().push("Test")
        self.assertEqual(queue().count(), 1)

        clear_queue()
        self.assertEqual(queue().count(), 0)

    @patch("smtplib.SMTP")
    def test_relay(self, smtp_mock):
        relay_obj = relay(port=0)
        smtp_mock.return_value = Mock()

        relay_obj.send('test@localhost', 'zedshaw@localhost', 'Test message', 'Test body')

        self.assertEqual(smtp_mock.return_value.sendmail.call_count, 1)
        self.assertEqual(smtp_mock.return_value.quit.call_count, 1)

    def test_delivered(self):
        clear_queue()
        queue().push("To: gooduser@localhost\nFrom: tester@localhost\n\nHi\n")

        assert delivered("gooduser@localhost"), "Test message not delivered."
        assert not delivered("baduser@localhost")
        assert_in_state('tests.handlers.simple_fsm_mod', 'gooduser@localhost', 'tester@localhost', 'START')

    def test_RouterConversation(self):
        client = RouterConversation('tester@localhost', 'Test router conversations.')
        client.begin()
        client.say('testlist@localhost', 'This is a test')
        delivered('testlist@localhost'), "Test message not delivered."
