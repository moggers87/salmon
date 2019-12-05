import mailbox
import os
import shutil

from mock import Mock, patch

from salmon import mail, queue

from .setup_env import SalmonTestCase

BYTES_MESSAGE = u"""From: me@localhost
To: you@localhost
Subject: bob!

Blobcat""".encode()


class QueueTestCase(SalmonTestCase):
    use_safe = False

    @classmethod
    def setUpClass(cls):
        shutil.rmtree("run/big_queue", ignore_errors=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree("run/big_queue", ignore_errors=True)

    def test_push(self):
        q = queue.Queue("run/queue", safe=self.use_safe)
        q.clear()

        # the queue doesn't really care if its a request or response, as long
        # as the object answers to str(msg)
        msg = mail.MailResponse(To="test@localhost", From="test@localhost", Subject="Test", Body="Test")
        key = q.push(msg)

        assert key, "Didn't get a key for test_get push."

        return q

    def test_pop(self):
        q = self.test_push()
        key, msg = q.pop()

        assert key, "Didn't get a key for test_get push."
        assert msg, "Didn't get a message for key %r" % key

        assert hasattr(msg, "Data"), "MailRequest doesn't have Data attribute"

        self.assertEqual(msg['to'], "test@localhost")
        self.assertEqual(msg['from'], "test@localhost")
        self.assertEqual(msg['subject'], "Test")
        self.assertEqual(msg.body(), "Test")

        self.assertEqual(q.count(), 0)
        assert not q.pop()[0]

    def test_get(self):
        q = self.test_push()
        msg = mail.MailResponse(To="test@localhost", From="test@localhost", Subject="Test", Body="Test")

        key = q.push(str(msg))
        assert key, "Didn't get a key for test_get push."

        msg = q.get(key)
        assert msg, "Didn't get a message for key %r" % key

    def test_remove(self):
        q = self.test_push()
        msg = mail.MailResponse(To="test@localhost", From="test@localhost", Subject="Test", Body="Test")

        key = q.push(str(msg))
        assert key, "Didn't get a key for test_get push."
        self.assertEqual(q.count(), 2)

        q.remove(key)
        self.assertEqual(q.count(), 1)

    def test_safe_maildir(self):
        self.use_safe = True
        self.test_push()
        self.test_pop()
        self.test_get()
        self.test_remove()

    def test_oversize_protections(self):
        # first just make an oversize limited queue
        overq = queue.Queue("run/queue", pop_limit=10)
        overq.clear()

        for i in range(5):
            overq.push("HELLO" * 100)

        self.assertEqual(overq.count(), 5)

        key, msg = overq.pop()

        assert not key and not msg, "Should get no messages."
        self.assertEqual(overq.count(), 0)

        # now make sure that oversize mail is moved to the overq
        overq = queue.Queue("run/queue", pop_limit=10, oversize_dir="run/big_queue")
        moveq = queue.Queue("run/big_queue")
        moveq.clear()

        for i in range(5):
            overq.push("HELLO" * 100)

        key, msg = overq.pop()

        assert not key and not msg, "Should get no messages."
        self.assertEqual(overq.count(), 0)
        self.assertEqual(moveq.count(), 5)

        moveq.clear()
        overq.clear()

    @patch('os.stat', new=Mock())
    def test_SafeMaildir_name_clash(self):
        sq = queue.SafeMaildir('run/queue')
        with self.assertRaises(mailbox.ExternalClashError):
            sq.add("TEST")

    @patch('mailbox._create_carefully', new=Mock())
    def test_SafeMaildir_throws_errno_failure(self):
        mailbox._create_carefully.side_effect = OSError
        sq = queue.SafeMaildir('run/queue')
        with self.assertRaises(OSError):
            sq.add('TEST')

    @patch('os.stat', new=Mock())
    def test_SafeMaildir_reraise_weird_errno(self):
        os.stat.side_effect = OSError
        sq = queue.SafeMaildir('run/queue')
        with self.assertRaises(OSError):
            sq.add('TEST')

    def test_bytes(self):
        """Test that passing a queue raw data works, i.e. as happens in the
        undeliverable queue"""
        q = queue.Queue("run/queue", safe=self.use_safe)
        q.clear()

        key = q.push(BYTES_MESSAGE)
        assert key, "Didn't get a key"

        mail = q.get(key)

        assert mail is not None, "Failed to get email from queue"

        self.assertEqual(mail['from'], "me@localhost")
        self.assertEqual(mail['to'], "you@localhost")
        self.assertEqual(mail['subject'], "bob!")
        self.assertEqual(mail.body(), "Blobcat")

    def test_len(self):
        q = self.test_push()
        self.assertEqual(len(q), 1)

    def test_count(self):
        q = self.test_push()
        self.assertEqual(q.count(), 1)
