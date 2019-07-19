from mock import Mock, patch

from salmon import mail, view
from salmon.confirm import ConfirmationEngine, ConfirmationStorage
from salmon.queue import Queue
from salmon.testing import delivered, relay
import jinja2

from .setup_env import SalmonTestCase


class ConfirmationTestCase(SalmonTestCase):
    def setUp(self):
        super(ConfirmationTestCase, self).setUp()
        self.storage = ConfirmationStorage()
        self.engine = ConfirmationEngine('run/confirm', self.storage)
        view.LOADER = jinja2.Environment(loader=jinja2.FileSystemLoader('tests/data/templates'))

    def tearDown(self):
        super(ConfirmationTestCase, self).tearDown()
        view.LOADER = None

    def test_ConfirmationStorage(self):
        self.storage.store('testing', 'somedude@localhost',
                           '12345', '567890')
        secret, pending_id = self.storage.get('testing', 'somedude@localhost')
        self.assertEqual(secret, '12345')
        self.assertEqual(pending_id, '567890')

        self.storage.delete('testing', 'somedude@localhost')
        self.assertEqual(len(self.storage.confirmations), 0)

        self.storage.store('testing', 'somedude@localhost',
                           '12345', '567890')
        self.assertEqual(len(self.storage.confirmations), 1)
        self.storage.clear()
        self.assertEqual(len(self.storage.confirmations), 0)

    @patch("smtplib.SMTP")
    def test_ConfirmationEngine_send(self, smtp_mock):
        smtp_mock.return_value = Mock()

        Queue('run/queue').clear()
        self.engine.clear()

        list_name = 'testing'
        action = 'subscribing to'
        host = 'localhost'

        message = mail.MailRequest('fakepeer', 'somedude@localhost',
                                   'testing-subscribe@localhost', 'Fake body.')

        self.engine.send(relay(port=0), 'testing', message, 'confirmation.msg', locals())

        self.assertEqual(smtp_mock.return_value.sendmail.call_count, 1)
        self.assertEqual(smtp_mock.return_value.quit.call_count, 1)
        assert delivered('somedude', to_queue=self.engine.pending)

        return smtp_mock.return_value.sendmail.call_args[0][2]

    def test_ConfirmationEngine_verify(self):
        confirm = self.test_ConfirmationEngine_send()
        confirm = mail.MailRequest(None, None, None, confirm)

        resp = mail.MailRequest('fakepeer', '"Somedude Smith" <somedude@localhost>', confirm['Reply-To'], 'Fake body')

        target, _, expect_secret = confirm['Reply-To'].split('-')
        expect_secret = expect_secret.split('@')[0]

        found = self.engine.verify(target, resp['from'], 'invalid_secret')
        assert not found

        pending = self.engine.verify(target, resp['from'], expect_secret)
        assert pending, "Verify failed: %r not in %r." % (expect_secret,
                                                          self.storage.confirmations)

        self.assertEqual(pending['from'], 'somedude@localhost')
        self.assertEqual(pending['to'], 'testing-subscribe@localhost')

    def test_ConfirmationEngine_cancel(self):
        confirm = self.test_ConfirmationEngine_send()
        confirm = mail.MailRequest(None, None, None, confirm)

        target, _, expect_secret = confirm['Reply-To'].split('-')
        expect_secret = expect_secret.split('@')[0]

        self.engine.cancel(target, confirm['To'], expect_secret)

        found = self.engine.verify(target, confirm['To'], expect_secret)
        assert not found
