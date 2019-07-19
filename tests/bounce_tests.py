from salmon import mail
from salmon.routing import Router

from .handlers import bounce_filtered_mod
from .setup_env import SalmonTestCase


class BounceTestCase(SalmonTestCase):
    def setUp(self):
        super(BounceTestCase, self).setUp()
        Router.load(["tests.handlers.bounce_filtered_mod"])
        Router.reload()

    def tearDown(self):
        super(BounceTestCase, self).tearDown()
        Router.HANDLERS.clear()
        Router.reload()

    def test_bounce_analyzer_on_bounce(self):
        with open("tests/data/bounce.msg") as file_obj:
            bm = mail.MailRequest(None, None, None, file_obj.read())
        assert bm.is_bounce()
        assert bm.bounce
        self.assertEqual(bm.bounce.score, 1.0)
        assert bm.bounce.probable()
        self.assertEqual(bm.bounce.primary_status, (5, u'Permanent Failure'))
        self.assertEqual(bm.bounce.secondary_status, (1, u'Addressing Status'))
        self.assertEqual(bm.bounce.combined_status, (11, u'Bad destination mailbox address'))

        assert bm.bounce.is_hard()
        self.assertEqual(bm.bounce.is_hard(), not bm.bounce.is_soft())

        self.assertEqual(bm.bounce.remote_mta, u'gmail-smtp-in.l.google.com')
        self.assertEqual(bm.bounce.reporting_mta, u'mail.zedshaw.com')
        self.assertEqual(bm.bounce.final_recipient,
                         u'asdfasdfasdfasdfasdfasdfewrqertrtyrthsfgdfgadfqeadvxzvz@gmail.com')
        self.assertEqual(bm.bounce.diagnostic_codes[0], u'550-5.1.1')
        self.assertEqual(bm.bounce.action, 'failed')
        assert 'Content-Description-Parts' in bm.bounce.headers

        assert bm.bounce.error_for_humans()

    def test_bounce_analyzer_on_regular(self):
        with open("tests/data/signed.msg") as file_obj:
            bm = mail.MailRequest(None, None, None, file_obj.read())
        assert not bm.is_bounce()
        assert bm.bounce
        self.assertEqual(bm.bounce.score, 0.0)
        assert not bm.bounce.probable()
        self.assertEqual(bm.bounce.primary_status, (None, None))
        self.assertEqual(bm.bounce.secondary_status, (None, None))
        self.assertEqual(bm.bounce.combined_status, (None, None))

        assert not bm.bounce.is_hard()
        assert not bm.bounce.is_soft()

        self.assertEqual(bm.bounce.remote_mta, None)
        self.assertEqual(bm.bounce.reporting_mta, None)
        self.assertEqual(bm.bounce.final_recipient, None)
        self.assertEqual(bm.bounce.diagnostic_codes, [None, None])
        self.assertEqual(bm.bounce.action, None)

    def test_bounce_to_decorator(self):
        with open("tests/data/bounce.msg") as file_obj:
            msg = mail.MailRequest(None, None, None, file_obj.read())

        Router.deliver(msg)
        assert Router.in_state(bounce_filtered_mod.START, msg)
        assert bounce_filtered_mod.HARD_RAN, "Hard bounce state didn't actually run: %r" % msg.To

        msg.bounce.primary_status = (4, u'Persistent Transient Failure')
        Router.clear_states()
        Router.deliver(msg)
        assert Router.in_state(bounce_filtered_mod.START, msg)
        assert bounce_filtered_mod.SOFT_RAN, "Soft bounce didn't actually run."

        with open("tests/data/signed.msg") as file_obj:
            msg = mail.MailRequest(None, None, None, file_obj.read())
        Router.clear_states()
        Router.deliver(msg)
        assert Router.in_state(bounce_filtered_mod.END, msg), "Regular messages aren't delivering."

    def test_bounce_getting_original(self):
        with open("tests/data/bounce.msg") as file_obj:
            msg = mail.MailRequest(None, None, None, file_obj.read())
        msg.is_bounce()

        assert msg.bounce.notification
        assert msg.bounce.notification.body

        assert msg.bounce.report

        for part in msg.bounce.report:
            assert [(k, part[k]) for k in part]
            # these are usually empty, but might not be.  they are in our test
            assert not part.body

        assert msg.bounce.original
        self.assertEqual(msg.bounce.original['to'], msg.bounce.final_recipient)
        assert msg.bounce.original.body

    def test_bounce_no_headers_error_message(self):
        msg = mail.MailRequest(None, None, None, "Nothing")
        msg.is_bounce()
        self.assertEqual(msg.bounce.error_for_humans(), 'No status codes found in bounce message.')
