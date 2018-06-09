# Copyright (C) 2008 Zed A. Shaw.  Licensed under the terms of the GPLv3.
from __future__ import print_function

import sys
import socket

from mock import Mock, patch
from nose.tools import assert_equal, assert_raises, with_setup
import lmtpd
import six

from salmon import mail, server, queue, routing

from .message_tests import (
    test_mail_request,
    test_mail_response_attachments,
    test_mail_response_html,
    test_mail_response_html_and_plain_text,
    test_mail_response_plain_text,
)
from .setup_env import setup_salmon_dirs, teardown_salmon_dirs


SMTP_MESSAGE_DEFS = {
    2: {"ok": u"250 Ok\r\n".encode()},
    3: {"ok": u"250 OK\r\n".encode()},
}

SMTP_MESSAGES = SMTP_MESSAGE_DEFS[sys.version_info[0]]


def test_router():
    routing.Router.deliver(test_mail_request())

    # test that fallthrough works too
    msg = test_mail_request()
    msg['to'] = 'unhandled@localhost'
    msg.To = msg['to']

    routing.Router.deliver(msg)


@patch("asynchat.async_chat.push")
def test_SMTPChannel(push_mock):
    channel = server.SMTPChannel(Mock(), Mock(), Mock())
    expected_version = u"220 {} {}\r\n".format(socket.getfqdn(), server.smtpd.__version__).encode()

    assert_equal(push_mock.call_args[0][1:], (expected_version,))
    assert_equal(type(push_mock.call_args[0][1]), six.binary_type)

    push_mock.reset_mock()
    channel.seen_greeting = True
    channel.smtp_MAIL("FROM: you@example.com\r\n")
    assert_equal(push_mock.call_args[0][1:], (SMTP_MESSAGES["ok"],))

    push_mock.reset_mock()
    channel.smtp_RCPT("TO: me@example.com")
    assert_equal(push_mock.call_args[0][1:], (SMTP_MESSAGES["ok"],))

    push_mock.reset_mock()
    channel.smtp_RCPT("TO: them@example.com")
    assert_equal(push_mock.call_args[0][1:],
                 (u"451 Will not accept multiple recipients in one transaction\r\n".encode(),))


def test_SMTPReceiver_process_message():
    receiver = server.SMTPReceiver(host="localhost", port=0)
    msg = test_mail_request()

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
        assert_equal(response, "450 Not found")

    # Python 3's smtpd takes some extra kawrgs, but i we don't care about that at the moment
    with patch("salmon.server.routing.Router") as router_mock, \
            patch("salmon.server.undeliverable_message"):
        response = receiver.process_message(msg.Peer, msg.From, msg.To, str(msg), mail_options=[], rcpt_options=[])
        assert response is None, response


@patch("lmtpd.asynchat.async_chat.push")
def test_LMTPChannel(push_mock):
    channel = lmtpd.LMTPChannel(Mock(), Mock(), Mock())
    expected_version = u"220 {} {}\r\n".format(socket.getfqdn(), server.lmtpd.__version__).encode()

    assert_equal(push_mock.call_args[0][1:], (expected_version,))
    assert_equal(type(push_mock.call_args[0][1]), six.binary_type)

    push_mock.reset_mock()
    channel.seen_greeting = True
    channel.lmtp_MAIL(b"FROM: you@example.com\r\n")
    assert_equal(push_mock.call_args[0][1:], (u"250 2.1.0 Ok\r\n".encode(),))

    push_mock.reset_mock()
    channel.lmtp_RCPT(b"TO: me@example.com")
    assert_equal(push_mock.call_args[0][1:], (u"250 2.1.0 Ok\r\n".encode(),))

    push_mock.reset_mock()
    channel.lmtp_RCPT(b"TO: them@example.com")
    assert_equal(push_mock.call_args[0][1:], (u"250 2.1.0 Ok\r\n".encode(),))


def test_LMTPReceiver_process_message():
    receiver = server.LMTPReceiver(host="localhost", port=0)
    msg = test_mail_request()

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
        assert_equal(response, "450 Not found")

    # lmtpd's server is a subclass of smtpd's server, so we should support the same kwargs here
    with patch("salmon.server.routing.Router") as router_mock, \
            patch("salmon.server.undeliverable_message"):
        response = receiver.process_message(msg.Peer, msg.From, msg.To, str(msg), mail_options=[], rcpt_options=[])
        assert response is None, response


@patch("salmon.queue.Queue")
def test_QueueReceiver_process_message(queue_mock):
    receiver = server.QueueReceiver("run/queue/thingy")
    msg = test_mail_request()

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


def test_Relay_asserts_ssl_options():
    """Relay raises an AssertionError if the ssl option is used in combination with starttls or lmtp"""
    with assert_raises(AssertionError):
        server.Relay("localhost", ssl=True, starttls=True)

    with assert_raises(AssertionError):
        server.Relay("localhost", ssl=True, lmtp=True)

    with assert_raises(AssertionError):
        server.Relay("localhost", ssl=True, starttls=True, lmtp=True)

    # no error
    server.Relay("localhost", starttls=True, lmtp=True)


@patch("salmon.server.smtplib.SMTP")
def test_relay_deliver(client_mock):
    # test that relay will actually call smtplib.SMTP
    relay = server.Relay("localhost", port=0)

    relay.deliver(test_mail_response_plain_text())
    assert_equal(client_mock.return_value.sendmail.call_count, 1)

    relay.deliver(test_mail_response_html())
    assert_equal(client_mock.return_value.sendmail.call_count, 2)

    relay.deliver(test_mail_response_html_and_plain_text())
    assert_equal(client_mock.return_value.sendmail.call_count, 3)

    relay.deliver(test_mail_response_attachments())
    assert_equal(client_mock.return_value.sendmail.call_count, 4)


@patch("salmon.server.smtplib.SMTP")
def test_relay_smtp(client_mock):
    relay = server.Relay("localhost", port=0)
    relay.deliver(test_mail_response_plain_text())
    assert_equal(client_mock.return_value.sendmail.call_count, 1)
    assert_equal(client_mock.return_value.starttls.call_count, 0)

    client_mock.reset_mock()
    relay = server.Relay("localhost", port=0, starttls=True)
    relay.deliver(test_mail_response_plain_text())
    assert_equal(client_mock.return_value.sendmail.call_count, 1)
    assert_equal(client_mock.return_value.starttls.call_count, 1)


@patch("salmon.server.smtplib.LMTP")
def test_relay_lmtp(client_mock):
    relay = server.Relay("localhost", port=0, lmtp=True)
    relay.deliver(test_mail_response_plain_text())
    assert_equal(client_mock.return_value.sendmail.call_count, 1)


@patch("salmon.server.smtplib.SMTP_SSL")
def test_relay_smtp_ssl(client_mock):
    relay = server.Relay("localhost", port=0, ssl=True)
    relay.deliver(test_mail_response_plain_text())
    assert_equal(client_mock.return_value.sendmail.call_count, 1)


@patch('salmon.server.resolver.query')
@patch("salmon.server.smtplib.SMTP")
def test_relay_deliver_mx_hosts(client_mock, query):
    query.return_value = [Mock()]
    query.return_value[0].exchange = "localhost"
    relay = server.Relay(None, port=0)

    msg = test_mail_response_plain_text()
    msg['to'] = 'user@localhost'
    relay.deliver(msg)
    assert_equal(query.call_count, 1)


@patch('salmon.server.resolver.query')
def test_relay_resolve_relay_host(query):
    from dns import resolver
    query.side_effect = resolver.NoAnswer
    relay = server.Relay(None, port=0)
    host = relay.resolve_relay_host('user@localhost')
    assert_equal(host, 'localhost')
    assert_equal(query.call_count, 1)

    query.reset_mock()
    query.side_effect = None  # reset_mock doens't clear return_value or side_effect
    query.return_value = [Mock()]
    query.return_value[0].exchange = "mx.example.com"
    host = relay.resolve_relay_host('user@example.com')
    assert_equal(host, 'mx.example.com')
    assert_equal(query.call_count, 1)


@patch("salmon.server.smtplib.SMTP")
def test_relay_reply(client_mock):
    relay = server.Relay("localhost", port=0)
    print("Relay: %r" % relay)

    relay.reply(test_mail_request(), 'from@localhost', 'Test subject', 'Body')
    assert_equal(client_mock.return_value.sendmail.call_count, 1)


@patch("socket.create_connection")
def test_relay_raises_exception(create_mock):
    # previously, salmon would eat up socket errors and just log something. Not cool!
    create_mock.side_effect = socket.error
    relay = server.Relay("example.com", port=0)
    with assert_raises(socket.error):
        relay.deliver(test_mail_response_plain_text())


def raises_exception(*x, **kw):
    raise RuntimeError("Raised on purpose.")


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
@patch('salmon.routing.Router', new=Mock())
def test_queue_receiver():
    receiver = server.QueueReceiver('run/queue')
    run_queue = queue.Queue('run/queue')
    run_queue.push(str(test_mail_response_plain_text()))
    assert run_queue.count() > 0
    receiver.start(one_shot=True)
    assert_equal(run_queue.count(), 0)

    routing.Router.deliver.side_effect = raises_exception
    receiver.process_message(mail.MailRequest('localhost', 'test@localhost', 'test@localhost', 'Fake body.'))


@patch('threading.Thread', new=Mock())
@patch('salmon.routing.Router', new=Mock())
def test_SMTPReceiver():
    receiver = server.SMTPReceiver(port=0)
    receiver.start()
    receiver.process_message('localhost', 'test@localhost', 'test@localhost',
                             'Fake body.')

    routing.Router.deliver.side_effect = raises_exception
    receiver.process_message('localhost', 'test@localhost', 'test@localhost', 'Fake body.')

    receiver.close()


def test_SMTPError():
    err = server.SMTPError(550)
    assert_equal(str(err), '550 Permanent Failure Mail Delivery Protocol Status')

    err = server.SMTPError(400)
    assert_equal(str(err), '400 Persistent Transient Failure Other or Undefined Status')

    err = server.SMTPError(425)
    assert_equal(str(err), '425 Persistent Transient Failure Mailbox Status')

    err = server.SMTPError(999)
    assert_equal(str(err), "999 ")

    err = server.SMTPError(999, "Bogus Error Code")
    assert_equal(str(err), "999 Bogus Error Code")
