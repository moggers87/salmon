# Copyright (C) 2008 Zed A. Shaw.  Licensed under the terms of the GPLv3.
from smtplib import LMTP, SMTP, SMTPDataError
from unittest.mock import Mock, call, patch
import os
import socket
import tempfile

from salmon import mail, queue, routing, server

from .setup_env import SalmonTestCase

SMTP_MESSAGES = {"ok": "250 OK\r\n".encode()}


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


class RelayTestCase(SalmonTestCase):
    def test_Relay_asserts_ssl_options(self):
        """Relay raises an TypeError if the ssl option is used in combination with starttls or lmtp"""
        with self.assertRaises(TypeError):
            server.Relay("localhost", ssl=True, starttls=True)

        with self.assertRaises(TypeError):
            server.Relay("localhost", ssl=True, lmtp=True)

        with self.assertRaises(TypeError):
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


class QueueTestCase(SalmonTestCase):
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


class SmtpSeverTestCase(SalmonTestCase):
    def setUp(self):
        super().setUp()
        self.server = server.SMTPReceiver(host="127.0.0.1", port=9999)
        self.server.start()
        self.addCleanup(self.server.stop)

    @patch('salmon.routing.Router')
    def test_message_routed(self, router_mock):
        with SMTP(self.server.host, self.server.port) as client:
            result = client.sendmail("you@localhost", "me@localhost", "hello")
            self.assertEqual(result, {})

            self.assertEqual(router_mock.deliver.call_count, 1)
            msg = router_mock.deliver.call_args[0][0]
            self.assertEqual(msg.Peer, client.sock.getsockname())
            self.assertEqual(msg.To, "me@localhost")
            self.assertEqual(msg.From, "you@localhost")
            self.assertEqual(msg.Data, b"hello")

    @patch('salmon.routing.Router')
    def test_message_routed_error(self, router_mock):
        router_mock.deliver.side_effect = RuntimeError("Raised on purpose")
        with SMTP(self.server.host, self.server.port) as client:
            result = client.sendmail("you@localhost", "me@localhost", "hello")
            self.assertEqual(result, {})

            self.assertEqual(router_mock.deliver.call_count, 1)
            msg = router_mock.deliver.call_args[0][0]
            self.assertEqual(msg.Peer, client.sock.getsockname())
            self.assertEqual(msg.To, "me@localhost")
            self.assertEqual(msg.From, "you@localhost")
            self.assertEqual(msg.Data, b"hello")

    @patch('salmon.routing.Router')
    def test_message_routed_smtperror(self, router_mock):
        router_mock.deliver.side_effect = server.SMTPError(450, "Raised on purpose")
        with SMTP(self.server.host, self.server.port) as client:
            with self.assertRaises(SMTPDataError):
                client.sendmail("you@localhost", "me@localhost", "hello")

            self.assertEqual(router_mock.deliver.call_count, 1)
            msg = router_mock.deliver.call_args[0][0]
            self.assertEqual(msg.Peer, client.sock.getsockname())
            self.assertEqual(msg.To, "me@localhost")
            self.assertEqual(msg.From, "you@localhost")
            self.assertEqual(msg.Data, b"hello")

    def test_multiple_rcpts(self):
        with SMTP(self.server.host, self.server.port) as client:
            code, _ = client.ehlo("localhost")
            self.assertEqual(code, 250)
            code, _ = client.mail("me@localhost")
            self.assertEqual(code, 250)
            code, _ = client.rcpt("you@localhost")
            self.assertEqual(code, 250)
            code, _ = client.rcpt("them@localhost")
            self.assertEqual(code, 451)


class LmtpSeverTestCase(SalmonTestCase):
    def setUp(self):
        super().setUp()
        self.server = server.LMTPReceiver(host="127.0.0.1", port=9999)
        self.server.start()
        self.addCleanup(self.server.stop)

    @patch('salmon.routing.Router')
    def test_message_routed(self, router_mock):
        with LMTP(self.server.host, self.server.port) as client:
            result = client.sendmail("you@localhost", "me@localhost", "hello")
            self.assertEqual(result, {})

            self.assertEqual(router_mock.deliver.call_count, 1)
            msg = router_mock.deliver.call_args[0][0]
            self.assertEqual(msg.Peer, client.sock.getsockname())
            self.assertEqual(msg.To, "me@localhost")
            self.assertEqual(msg.From, "you@localhost")
            self.assertEqual(msg.Data, b"hello")

    @patch('salmon.routing.Router')
    def test_message_routed_error(self, router_mock):
        router_mock.deliver.side_effect = RuntimeError("Raised on purpose")
        with LMTP(self.server.host, self.server.port) as client:
            result = client.sendmail("you@localhost", "me@localhost", "hello")
            self.assertEqual(result, {})

            self.assertEqual(router_mock.deliver.call_count, 1)
            msg = router_mock.deliver.call_args[0][0]
            self.assertEqual(msg.Peer, client.sock.getsockname())
            self.assertEqual(msg.To, "me@localhost")
            self.assertEqual(msg.From, "you@localhost")
            self.assertEqual(msg.Data, b"hello")

    @patch('salmon.routing.Router')
    def test_message_routed_smtperror(self, router_mock):
        router_mock.deliver.side_effect = server.SMTPError(450, "Raised on purpose")
        with LMTP(self.server.host, self.server.port) as client:
            with self.assertRaises(SMTPDataError):
                client.sendmail("you@localhost", "me@localhost", "hello")

            self.assertEqual(router_mock.deliver.call_count, 1)
            msg = router_mock.deliver.call_args[0][0]
            self.assertEqual(msg.Peer, client.sock.getsockname())
            self.assertEqual(msg.To, "me@localhost")
            self.assertEqual(msg.From, "you@localhost")
            self.assertEqual(msg.Data, b"hello")

    def test_multiple_rcpts(self):
        with LMTP(self.server.host, self.server.port) as client:
            code, _ = client.ehlo("localhost")
            self.assertEqual(code, 250)
            code, _ = client.mail("me@localhost")
            self.assertEqual(code, 250)
            code, _ = client.rcpt("you@localhost")
            self.assertEqual(code, 250)
            code, _ = client.rcpt("them@localhost")
            self.assertEqual(code, 250)


class AsyncSmtpServerTestCase(SalmonTestCase):
    def setUp(self):
        super().setUp()
        self.server = server.AsyncSMTPReceiver(hostname="127.0.0.1", port=9999)
        self.server.start()
        self.addCleanup(self.server.stop)

    @patch('salmon.routing.Router')
    def test_message_routed(self, router_mock):
        with SMTP(self.server.hostname, self.server.port) as client:
            result = client.sendmail("you@localhost", "me@localhost", "hello")
            self.assertEqual(result, {})

            self.assertEqual(router_mock.deliver.call_count, 1)
            msg = router_mock.deliver.call_args[0][0]
            self.assertEqual(msg.Peer, client.sock.getsockname())
            self.assertEqual(msg.To, "me@localhost")
            self.assertEqual(msg.From, "you@localhost")
            self.assertEqual(msg.Data, b"hello")

    @patch('salmon.routing.Router')
    def test_message_routed_error(self, router_mock):
        router_mock.deliver.side_effect = RuntimeError("Raised on purpose")
        with SMTP(self.server.hostname, self.server.port) as client:
            result = client.sendmail("you@localhost", "me@localhost", "hello")
            self.assertEqual(result, {})

            self.assertEqual(router_mock.deliver.call_count, 1)
            msg = router_mock.deliver.call_args[0][0]
            self.assertEqual(msg.Peer, client.sock.getsockname())
            self.assertEqual(msg.To, "me@localhost")
            self.assertEqual(msg.From, "you@localhost")
            self.assertEqual(msg.Data, b"hello")

    @patch('salmon.routing.Router')
    def test_message_routed_smtperror(self, router_mock):
        router_mock.deliver.side_effect = server.SMTPError(450, "Raised on purpose")
        with SMTP(self.server.hostname, self.server.port) as client:
            with self.assertRaises(SMTPDataError):
                client.sendmail("you@localhost", "me@localhost", "hello")

            self.assertEqual(router_mock.deliver.call_count, 1)
            msg = router_mock.deliver.call_args[0][0]
            self.assertEqual(msg.Peer, client.sock.getsockname())
            self.assertEqual(msg.To, "me@localhost")
            self.assertEqual(msg.From, "you@localhost")
            self.assertEqual(msg.Data, b"hello")

    def test_multiple_rcpts(self):
        with SMTP(self.server.hostname, self.server.port) as client:
            code, _ = client.ehlo("localhost")
            self.assertEqual(code, 250)
            code, _ = client.mail("me@localhost")
            self.assertEqual(code, 250)
            code, _ = client.rcpt("you@localhost")
            self.assertEqual(code, 250)
            code, _ = client.rcpt("them@localhost")
            self.assertEqual(code, 451)


class AsyncLmtpServerTestCase(SalmonTestCase):
    def setUp(self):
        super().setUp()
        self.server = server.AsyncLMTPReceiver(hostname="127.0.0.1", port=9999)
        self.server.start()
        self.addCleanup(self.server.stop)

    @patch('salmon.routing.Router')
    def test_message_routed(self, router_mock):
        with LMTP(self.server.hostname, self.server.port) as client:
            result = client.sendmail("you@localhost", "me@localhost", "hello")
            self.assertEqual(result, {})

            self.assertEqual(router_mock.deliver.call_count, 1)
            msg = router_mock.deliver.call_args[0][0]
            self.assertEqual(msg.Peer, client.sock.getsockname())
            self.assertEqual(msg.To, "me@localhost")
            self.assertEqual(msg.From, "you@localhost")
            self.assertEqual(msg.Data, b"hello")

    @patch('salmon.routing.Router')
    def test_message_routed_error(self, router_mock):
        router_mock.deliver.side_effect = RuntimeError("Raised on purpose")
        with LMTP(self.server.hostname, self.server.port) as client:
            result = client.sendmail("you@localhost", "me@localhost", "hello")
            self.assertEqual(result, {})

            self.assertEqual(router_mock.deliver.call_count, 1)
            msg = router_mock.deliver.call_args[0][0]
            self.assertEqual(msg.Peer, client.sock.getsockname())
            self.assertEqual(msg.To, "me@localhost")
            self.assertEqual(msg.From, "you@localhost")
            self.assertEqual(msg.Data, b"hello")

    @patch('salmon.routing.Router')
    def test_message_routed_smtperror(self, router_mock):
        router_mock.deliver.side_effect = server.SMTPError(450, "Raised on purpose")
        with LMTP(self.server.hostname, self.server.port) as client:
            with self.assertRaises(SMTPDataError):
                client.sendmail("you@localhost", "me@localhost", "hello")

            self.assertEqual(router_mock.deliver.call_count, 1)
            msg = router_mock.deliver.call_args[0][0]
            self.assertEqual(msg.Peer, client.sock.getsockname())
            self.assertEqual(msg.To, "me@localhost")
            self.assertEqual(msg.From, "you@localhost")
            self.assertEqual(msg.Data, b"hello")

    def test_multiple_rcpts(self):
        with LMTP(self.server.hostname, self.server.port) as client:
            code, _ = client.ehlo("localhost")
            self.assertEqual(code, 250)
            code, _ = client.mail("me@localhost")
            self.assertEqual(code, 250)
            code, _ = client.rcpt("you@localhost")
            self.assertEqual(code, 250)
            code, _ = client.rcpt("them@localhost")
            self.assertEqual(code, 250)


class LmtpSeverUnixSocketTestCase(SalmonTestCase):
    def test_asyncio(self):
        tempdir = tempfile.mkdtemp()
        socket_name = os.path.join(tempdir, "lmtp")
        _server = server.AsyncLMTPReceiver(socket=socket_name)
        _server.start()
        self.addCleanup(_server.stop)

        with LMTP(socket_name) as client:
            code, _ = client.ehlo("localhost")
            self.assertEqual(code, 250)

    def test_asyncore(self):
        tempdir = tempfile.mkdtemp()
        socket_name = os.path.join(tempdir, "lmtp")
        _server = server.LMTPReceiver(socket=socket_name)
        _server.start()
        self.addCleanup(_server.stop)

        with LMTP(socket_name) as client:
            code, _ = client.ehlo("localhost")
            self.assertEqual(code, 250)
