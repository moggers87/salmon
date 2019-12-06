# Copyright (C) 2008 Zed A. Shaw.  Licensed under the terms of the GPLv3.
from __future__ import print_function

import socket
import sys

from mock import Mock, call, patch
import lmtpd
import six

from salmon import mail, queue, routing, server

from .setup_env import SalmonTestCase

SMTP_MESSAGE_DEFS = {
    2: {"ok": u"250 Ok\r\n".encode()},
    3: {"ok": u"250 OK\r\n".encode()},
}

SMTP_MESSAGES = SMTP_MESSAGE_DEFS[sys.version_info[0]]


def generate_mail(factory=mail.MailRequest, peer="localhost", From="from@localhost", To="to@localhost",
                  Data="body", attachment=False):
    msg = factory(peer, From, To, Data)
    if attachment:
        msg.attach("./README.rst", content_type="text/plain", disposition="inline")
    return msg


class ServerTestCase(SalmonTestCase):
    def test_router(self):
        routing.Router.deliver(generate_mail())

        # test that fallthrough works too
        msg = generate_mail()
        msg['to'] = 'unhandled@localhost'
        msg.To = msg['to']

        routing.Router.deliver(msg)

    @patch("asynchat.async_chat.push")
    def test_SMTPChannel(self, push_mock):
        channel = server.SMTPChannel(Mock(), Mock(), Mock())
        expected_version = u"220 {} {}\r\n".format(socket.getfqdn(), server.smtpd.__version__).encode()

        self.assertEqual(push_mock.call_args[0][1:], (expected_version,))
        self.assertEqual(type(push_mock.call_args[0][1]), six.binary_type)

        push_mock.reset_mock()
        channel.seen_greeting = True
        channel.smtp_MAIL("FROM: you@example.com\r\n")
        self.assertEqual(push_mock.call_args[0][1:], (SMTP_MESSAGES["ok"],))

        push_mock.reset_mock()
        channel.smtp_RCPT("TO: me@example.com")
        self.assertEqual(push_mock.call_args[0][1:], (SMTP_MESSAGES["ok"],))

        push_mock.reset_mock()
        channel.smtp_RCPT("TO: them@example.com")
        self.assertEqual(push_mock.call_args[0][1:],
                         (u"451 Will not accept multiple recipients in one transaction\r\n".encode(),))

    def test_SMTPReceiver_process_message(self):
        receiver = server.SMTPReceiver(host="localhost", port=0)
        msg = generate_mail()

        with patch("salmon.server.routing.Router") as router_mock, \
                patch("salmon.server.undeliverable_message"):
            response = receiver.process_message(msg.Peer, msg.From, msg.To, str(msg))
            assert response is None, response

        with patch("salmon.server.routing.Router") as router_mock, \
                patch("salmon.server.undeliverable_message"):
            router_mock.deliver.side_effect = Exception()
            response = receiver.process_message(msg.Peer, msg.From, msg.To, str(msg))
            assert response is None, response

        with patch("salmon.server.routing.Router") as router_mock, \
                patch("salmon.server.undeliverable_message"):
            router_mock.deliver.side_effect = server.SMTPError(450, "Not found")
            response = receiver.process_message(msg.Peer, msg.From, msg.To, str(msg))
            self.assertEqual(response, "450 Not found")

        # Python 3's smtpd takes some extra kawrgs, but i we don't care about that at the moment
        with patch("salmon.server.routing.Router") as router_mock, \
                patch("salmon.server.undeliverable_message"):
            response = receiver.process_message(msg.Peer, msg.From, msg.To, str(msg), mail_options=[], rcpt_options=[])
            assert response is None, response

    @patch("lmtpd.asynchat.async_chat.push")
    def test_LMTPChannel(self, push_mock):
        channel = lmtpd.LMTPChannel(Mock(), Mock(), Mock())
        expected_version = u"220 {} {}\r\n".format(socket.getfqdn(), server.lmtpd.__version__).encode()

        self.assertEqual(push_mock.call_args[0][1:], (expected_version,))
        self.assertEqual(type(push_mock.call_args[0][1]), six.binary_type)

        push_mock.reset_mock()
        channel.seen_greeting = True
        channel.lmtp_MAIL(b"FROM: you@example.com\r\n")
        self.assertEqual(push_mock.call_args[0][1:], (u"250 2.1.0 Ok\r\n".encode(),))

        push_mock.reset_mock()
        channel.lmtp_RCPT(b"TO: me@example.com")
        self.assertEqual(push_mock.call_args[0][1:], (u"250 2.1.0 Ok\r\n".encode(),))

        push_mock.reset_mock()
        channel.lmtp_RCPT(b"TO: them@example.com")
        self.assertEqual(push_mock.call_args[0][1:], (u"250 2.1.0 Ok\r\n".encode(),))

    def test_LMTPReceiver_process_message(self):
        receiver = server.LMTPReceiver(host="localhost", port=0)
        msg = generate_mail()

        with patch("salmon.server.routing.Router") as router_mock, \
                patch("salmon.server.undeliverable_message"):
            response = receiver.process_message(msg.Peer, msg.From, msg.To, str(msg))
            assert response is None, response

        with patch("salmon.server.routing.Router") as router_mock, \
                patch("salmon.server.undeliverable_message"):
            router_mock.deliver.side_effect = Exception()
            response = receiver.process_message(msg.Peer, msg.From, msg.To, str(msg))
            assert response is None, response

        with patch("salmon.server.routing.Router") as router_mock, \
                patch("salmon.server.undeliverable_message"):
            router_mock.deliver.side_effect = server.SMTPError(450, "Not found")
            response = receiver.process_message(msg.Peer, msg.From, msg.To, str(msg))
            self.assertEqual(response, "450 Not found")

        # lmtpd's server is a subclass of smtpd's server, so we should support the same kwargs here
        with patch("salmon.server.routing.Router") as router_mock, \
                patch("salmon.server.undeliverable_message"):
            response = receiver.process_message(msg.Peer, msg.From, msg.To, str(msg), mail_options=[], rcpt_options=[])
            assert response is None, response

    @patch("salmon.queue.Queue")
    def test_QueueReceiver_process_message(self, queue_mock):
        receiver = server.QueueReceiver("run/queue/thingy")
        msg = generate_mail()

        with patch("salmon.server.routing.Router") as router_mock, \
                patch("salmon.server.undeliverable_message"):
            response = receiver.process_message(msg)
            assert response is None, response

        with patch("salmon.server.routing.Router") as router_mock, \
                patch("salmon.server.undeliverable_message"):
            router_mock.deliver.side_effect = Exception()
            response = receiver.process_message(msg)
            assert response is None, response

        with patch("salmon.server.routing.Router") as router_mock, \
                patch("salmon.server.undeliverable_message"):
            router_mock.deliver.side_effect = server.SMTPError(450, "Not found")
            response = receiver.process_message(msg)
            # queue doesn't actually support SMTPErrors
            assert response is None, response

    def test_Relay_asserts_ssl_options(self):
        """Relay raises an AssertionError if the ssl option is used in combination with starttls or lmtp"""
        with self.assertRaises(AssertionError):
            server.Relay("localhost", ssl=True, starttls=True)

        with self.assertRaises(AssertionError):
            server.Relay("localhost", ssl=True, lmtp=True)

        with self.assertRaises(AssertionError):
            server.Relay("localhost", ssl=True, starttls=True, lmtp=True)

        # no error
        server.Relay("localhost", starttls=True, lmtp=True)

    @patch("salmon.server.smtplib.SMTP")
    def test_relay_deliver(self, client_mock):
        # test that relay will actually call smtplib.SMTP
        relay = server.Relay("localhost", port=0)

        msg = generate_mail(factory=mail.MailResponse, attachment=True)
        relay.deliver(msg)
        self.assertEqual(client_mock.return_value.sendmail.call_count, 1)

        msg = generate_mail(factory=mail.MailResponse, attachment=True)
        relay.deliver(msg)
        self.assertEqual(client_mock.return_value.sendmail.call_count, 2)

        msg = generate_mail(factory=mail.MailResponse, attachment=True)
        relay.deliver(msg)
        self.assertEqual(client_mock.return_value.sendmail.call_count, 3)

        msg = generate_mail(factory=mail.MailResponse, attachment=True)
        relay.deliver(msg)
        self.assertEqual(client_mock.return_value.sendmail.call_count, 4)

    @patch("salmon.server.smtplib.SMTP")
    def test_relay_smtp(self, client_mock):
        relay = server.Relay("localhost", port=0)
        relay.deliver(generate_mail(factory=mail.MailResponse, attachment=True))
        self.assertEqual(client_mock.return_value.sendmail.call_count, 1)
        self.assertEqual(client_mock.return_value.starttls.call_count, 0)

        client_mock.reset_mock()
        relay = server.Relay("localhost", port=0, starttls=True)
        relay.deliver(generate_mail(factory=mail.MailResponse, attachment=True))
        self.assertEqual(client_mock.return_value.sendmail.call_count, 1)
        self.assertEqual(client_mock.return_value.starttls.call_count, 1)

    @patch("salmon.server.smtplib.LMTP")
    def test_relay_lmtp(self, client_mock):
        relay = server.Relay("localhost", port=0, lmtp=True)
        relay.deliver(generate_mail(factory=mail.MailResponse, attachment=True))
        self.assertEqual(client_mock.return_value.sendmail.call_count, 1)

    @patch("salmon.server.smtplib.SMTP_SSL")
    def test_relay_smtp_ssl(self, client_mock):
        relay = server.Relay("localhost", port=0, ssl=True)
        relay.deliver(generate_mail(factory=mail.MailResponse, attachment=True))
        self.assertEqual(client_mock.return_value.sendmail.call_count, 1)

    @patch('salmon.server.resolver.query')
    @patch("salmon.server.smtplib.SMTP")
    def test_relay_deliver_mx_hosts(self, client_mock, query):
        query.return_value = [Mock()]
        query.return_value[0].exchange = "localhost"
        relay = server.Relay(None, port=0)

        msg = generate_mail(factory=mail.MailResponse, attachment=True)
        msg['to'] = 'user@localhost'
        relay.deliver(msg)
        self.assertEqual(query.call_count, 1)

    @patch('salmon.server.resolver.query')
    def test_relay_resolve_relay_host(self, query):
        from dns import resolver
        query.side_effect = resolver.NoAnswer
        relay = server.Relay(None, port=0)
        host = relay.resolve_relay_host('user@localhost')
        self.assertEqual(host, 'localhost')
        self.assertEqual(query.call_count, 1)

        query.reset_mock()
        query.side_effect = None  # reset_mock doens't clear return_value or side_effect
        query.return_value = [Mock()]
        query.return_value[0].exchange = "mx.example.com"
        host = relay.resolve_relay_host('user@example.com')
        self.assertEqual(host, 'mx.example.com')
        self.assertEqual(query.call_count, 1)

    @patch("salmon.server.smtplib.SMTP")
    def test_relay_reply(self, client_mock):
        relay = server.Relay("localhost", port=0)
        print("Relay: %r" % relay)

        relay.reply(generate_mail(), 'from@localhost', 'Test subject', 'Body')
        self.assertEqual(client_mock.return_value.sendmail.call_count, 1)

    @patch("socket.create_connection")
    def test_relay_raises_exception(self, create_mock):
        # previously, salmon would eat up socket errors and just log something. Not cool!
        create_mock.side_effect = socket.error
        relay = server.Relay("example.com", port=0)
        with self.assertRaises(socket.error):
            relay.deliver(generate_mail(factory=mail.MailResponse))

    @patch('salmon.routing.Router')
    def test_queue_receiver(self, router_mock):
        receiver = server.QueueReceiver('run/queue')
        run_queue = queue.Queue('run/queue')
        run_queue.push(str(generate_mail(factory=mail.MailResponse)))
        assert run_queue.count() > 0
        receiver.start(one_shot=True)
        self.assertEqual(run_queue.count(), 0)
        self.assertEqual(run_queue.count(), 0)
        self.assertEqual(router_mock.deliver.call_count, 1)

        router_mock.deliver.side_effect = RuntimeError("Raised on purpose")
        receiver.process_message(mail.MailRequest('localhost', 'test@localhost', 'test@localhost', 'Fake body.'))

    @patch('salmon.routing.Router')
    @patch("salmon.server.queue.Queue")
    def test_queue_receiver_pop_error(self, queue_mock, router_mock):
        def key_error(*args, **kwargs):
            queue_mock.return_value.__len__.return_value = 0
            raise KeyError

        queue_mock.return_value.__len__.return_value = 1
        queue_mock.return_value.pop.side_effect = key_error
        receiver = server.QueueReceiver('run/queue')
        receiver.start(one_shot=True)
        self.assertEqual(queue_mock.return_value.pop.call_count, 1)
        self.assertEqual(router_mock.deliver.call_count, 0)

    @patch("salmon.server.time.sleep")
    @patch("salmon.server.Pool")
    def test_queue_receiver_sleep(self, pool_mock, sleep_mock):
        class SleepCalled(Exception):
            pass

        def sleepy(*args, **kwargs):
            if sleep_mock.call_count > 1:
                raise SleepCalled()

        sleep_mock.side_effect = sleepy

        receiver = server.QueueReceiver('run/queue', sleep=10, workers=1)
        with self.assertRaises(SleepCalled):
            receiver.start()

        self.assertEqual(receiver.workers.apply_async.call_count, 0)
        self.assertEqual(sleep_mock.call_count, 2)
        self.assertEqual(sleep_mock.call_args_list, [call(receiver.sleep), call(receiver.sleep)])

    @patch("salmon.server.Pool")
    def test_queue_receiver_pool(self, pool_mock):
        run_queue = queue.Queue('run/queue')
        msg = str(generate_mail(factory=mail.MailResponse))
        run_queue.push(msg)

        receiver = server.QueueReceiver('run/queue', sleep=10, workers=1)
        receiver.start(one_shot=True)

        self.assertEqual(receiver.workers.apply_async.call_count, 1)
        self.assertEqual(receiver.workers.apply_async.call_args[0], (receiver.process_message,))

        args = receiver.workers.apply_async.call_args[1]["args"]
        del receiver.workers.apply_async.call_args[1]["args"]

        # onlly the "args" kwarg should be present
        self.assertEqual(receiver.workers.apply_async.call_args[1], {})

        # we can't compare two Mail* objects, so we'll just check the type
        self.assertEqual(len(args), 1)
        self.assertEqual(type(args[0]), mail.MailRequest)

    @patch('threading.Thread', new=Mock())
    @patch('salmon.routing.Router', new=Mock())
    def test_SMTPReceiver(self):
        receiver = server.SMTPReceiver(port=0)
        receiver.start()
        receiver.process_message('localhost', 'test@localhost', 'test@localhost',
                                 'Fake body.')

        routing.Router.deliver.side_effect = RuntimeError("Raised on purpose")
        receiver.process_message('localhost', 'test@localhost', 'test@localhost', 'Fake body.')

        receiver.close()

    def test_SMTPError(self):
        err = server.SMTPError(550)
        self.assertEqual(str(err), '550 Permanent Failure Mail Delivery Protocol Status')

        err = server.SMTPError(400)
        self.assertEqual(str(err), '400 Persistent Transient Failure Other or Undefined Status')

        err = server.SMTPError(425)
        self.assertEqual(str(err), '425 Persistent Transient Failure Mailbox Status')

        err = server.SMTPError(999)
        self.assertEqual(str(err), "999 ")

        err = server.SMTPError(999, "Bogus Error Code")
        self.assertEqual(str(err), "999 Bogus Error Code")
