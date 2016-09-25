# Copyright (C) 2008 Zed A. Shaw.  Licensed under the terms of the GPLv3.
from mock import Mock, patch
from nose.tools import assert_equal, assert_raises, with_setup

from salmon import mail, server, queue, routing

from .message_tests import (
    test_mail_request,
    test_mail_response_attachments,
    test_mail_response_html,
    test_mail_response_html_and_plain_text,
    test_mail_response_plain_text,
)
from .setup_env import setup_salmon_dirs, teardown_salmon_dirs


def test_router():
    routing.Router.deliver(test_mail_request())

    # test that fallthrough works too
    msg = test_mail_request()
    msg['to'] = 'unhandled@localhost'
    msg.To = msg['to']

    routing.Router.deliver(msg)


def test_SMTPChannel_rcpt():
    channel = server.SMTPChannel(Mock(), Mock(), Mock())
    channel.push = Mock()
    channel.smtp_MAIL("FROM: you@example.com")

    channel.push.reset_mock()
    channel.smtp_RCPT("TO: me@example.com")
    assert_equal(channel.push.call_args[0], ("250 Ok",))

    channel.push.reset_mock()
    channel.smtp_RCPT("TO: them@example.com")
    assert_equal(channel.push.call_args[0], ("451 Will not accept multiple recipients in one transaction",))


def test_SMTPReceiver_process_message():
    receiver = server.SMTPReceiver(host="localhost", port=8895)
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


def test_LMTPReceiver_process_message():
    receiver = server.LMTPReceiver(host="localhost", port=8894)
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


def test_relay_deliver():
    # this test actually delivers to a test server
    relay = server.Relay("localhost", port=8899)

    relay.deliver(test_mail_response_plain_text())
    relay.deliver(test_mail_response_html())
    relay.deliver(test_mail_response_html_and_plain_text())
    relay.deliver(test_mail_response_attachments())


@patch("salmon.server.smtplib.SMTP")
def test_relay_smtp(client_mock):
    relay = server.Relay("localhost", port=8899)
    relay.deliver(test_mail_response_plain_text())
    assert_equal(client_mock.return_value.sendmail.call_count, 1)
    assert_equal(client_mock.return_value.starttls.call_count, 0)

    client_mock.reset_mock()
    relay = server.Relay("localhost", port=8899, starttls=True)
    relay.deliver(test_mail_response_plain_text())
    assert_equal(client_mock.return_value.sendmail.call_count, 1)
    assert_equal(client_mock.return_value.starttls.call_count, 1)


@patch("salmon.server.smtplib.LMTP")
def test_relay_lmtp(client_mock):
    relay = server.Relay("localhost", port=8899, lmtp=True)
    relay.deliver(test_mail_response_plain_text())
    assert_equal(client_mock.return_value.sendmail.call_count, 1)


@patch("salmon.server.smtplib.SMTP_SSL")
def test_relay_smtp_ssl(client_mock):
    relay = server.Relay("localhost", port=8899, ssl=True)
    relay.deliver(test_mail_response_plain_text())
    assert_equal(client_mock.return_value.sendmail.call_count, 1)


@patch('salmon.server.resolver.query')
def test_relay_deliver_mx_hosts(query):
    query.return_value = [Mock()]
    query.return_value[0].exchange = "localhost"
    relay = server.Relay(None, port=8899)

    msg = test_mail_response_plain_text()
    msg['to'] = 'user@localhost'
    relay.deliver(msg)
    assert query.called


@patch('salmon.server.resolver.query')
def test_relay_resolve_relay_host(query):
    from dns import resolver
    query.side_effect = resolver.NoAnswer
    relay = server.Relay(None, port=8899)
    host = relay.resolve_relay_host('user@localhost')
    assert_equal(host, 'localhost')
    assert query.called

    query.reset_mock()
    query.side_effect = None  # reset_mock doens't clear return_value or side_effect
    query.return_value = [Mock()]
    query.return_value[0].exchange = "mx.example.com"
    host = relay.resolve_relay_host('user@example.com')
    assert_equal(host, 'mx.example.com')
    assert query.called


def test_relay_reply():
    relay = server.Relay("localhost", port=8899)
    print "Relay: %r" % relay

    relay.reply(test_mail_request(), 'from@localhost', 'Test subject', 'Body')


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
    assert run_queue.count() == 0

    routing.Router.deliver.side_effect = raises_exception
    receiver.process_message(mail.MailRequest('localhost', 'test@localhost', 'test@localhost', 'Fake body.'))


@patch('threading.Thread', new=Mock())
@patch('salmon.routing.Router', new=Mock())
def test_SMTPReceiver():
    receiver = server.SMTPReceiver(port=9999)
    receiver.start()
    receiver.process_message('localhost', 'test@localhost', 'test@localhost',
                             'Fake body.')

    routing.Router.deliver.side_effect = raises_exception
    receiver.process_message('localhost', 'test@localhost', 'test@localhost', 'Fake body.')

    receiver.close()


def test_SMTPError():
    err = server.SMTPError(550)
    assert str(err) == '550 Permanent Failure Mail Delivery Protocol Status', "Error is wrong: %r" % str(err)

    err = server.SMTPError(400)
    assert str(err) == '400 Persistent Transient Failure Other or Undefined Status', "Error is wrong: %r" % str(err)

    err = server.SMTPError(425)
    assert str(err) == '425 Persistent Transient Failure Mailbox Status', "Error is wrong: %r" % str(err)

    err = server.SMTPError(999)
    assert str(err) == "999 ", "Error is wrong: %r" % str(err)

    err = server.SMTPError(999, "Bogus Error Code")
    assert str(err) == "999 Bogus Error Code"
