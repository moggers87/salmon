"""
The majority of the server related things Salmon needs to run, like receivers,
relays, and queue processors.
"""

import asyncore
import logging
import smtpd
import smtplib
import socket
import threading
import time
import traceback

from dns import resolver
import lmtpd

from salmon import queue, mail, routing, __version__
from salmon.bounce import PRIMARY_STATUS_CODES, SECONDARY_STATUS_CODES, COMBINED_STATUS_CODES


smtpd.__version__ = "Salmon Mail router SMTPD, version %s" % __version__
lmtpd.__version__ = "Salmon Mail router LMTPD, version %s" % __version__


def undeliverable_message(raw_message, failure_type):
    """
    Used universally in this file to shove totally screwed messages
    into the routing.Router.UNDELIVERABLE_QUEUE (if it's set).
    """
    if routing.Router.UNDELIVERABLE_QUEUE:
        key = routing.Router.UNDELIVERABLE_QUEUE.push(raw_message)

        logging.error("Failed to deliver message because of %r, put it in "
                      "undeliverable queue with key %r", failure_type, key)


class SMTPError(Exception):
    """
    You can raise this error when you want to abort with a SMTP error code to
    the client.  This is really only relevant when you're using the
    SMTPReceiver and the client understands the error.

    If you give a message than it'll use that, but it'll also produce a
    consistent error message based on your code.  It uses the errors in
    salmon.bounce to produce them.
    """
    def __init__(self, code, message=None):
        self.code = code
        self.message = message or self.error_for_code(code)

        Exception.__init__(self, "%d %s" % (self.code, self.message))

    def error_for_code(self, code):
        primary, secondary, tertiary = str(code)

        primary = PRIMARY_STATUS_CODES.get(primary, "")
        secondary = SECONDARY_STATUS_CODES.get(secondary, "")
        combined = COMBINED_STATUS_CODES.get(primary + secondary, "")

        return " ".join([primary, secondary, combined]).strip()


class Relay(object):
    """
    Used to talk to your "relay server" or smart host, this is probably the most
    important class in the handlers next to the salmon.routing.Router.
    It supports a few simple operations for sending mail, replying, and can
    log the protocol it uses to stderr if you set debug=1 on __init__.
    """
    def __init__(self, host='127.0.0.1', port=25, username=None, password=None,
                 ssl=False, starttls=False, debug=0, lmtp=False):
        """
        The hostname and port we're connecting to, and the debug level (default to 0).
        Optional username and password for smtp authentication.
        If ssl is True smtplib.SMTP_SSL will be used.
        If starttls is True (and ssl False), smtp connection will be put in TLS mode.
        If lmtp is true, then smtplib.LMTP will be used. Mutually exclusive with ssl.
        """
        self.hostname = host
        self.port = port
        self.debug = debug
        self.username = username
        self.password = password
        self.ssl = ssl
        self.starttls = starttls
        self.lmtp = lmtp

        assert not (ssl and lmtp), "LMTP over SSL not supported. Use STARTTLS instead."
        assert not (ssl and starttls), "SSL and STARTTLS make no sense together"

    def configure_relay(self, hostname):
        if self.ssl:
            relay_host = smtplib.SMTP_SSL(hostname, self.port)
        elif self.lmtp:
            relay_host = smtplib.LMTP(hostname, self.port)
        else:
            relay_host = smtplib.SMTP(hostname, self.port)

        relay_host.set_debuglevel(self.debug)

        if self.starttls:
            relay_host.starttls()
        if self.username and self.password:
            relay_host.login(self.username, self.password)

        assert relay_host, 'Code error, file a bug.'
        return relay_host

    def deliver(self, message, To=None, From=None):
        """
        Takes a fully formed email message and delivers it to the
        configured relay server.

        You can pass in an alternate To and From, which will be used in the
        SMTP/LMTP send lines rather than what's in the message.
        """
        # Check in multiple places for To and From.
        # Ordered in preference.
        recipient = To or getattr(message, 'To', None) or message['To']
        sender = From or getattr(message, 'From', None) or message['From']

        hostname = self.hostname or self.resolve_relay_host(recipient)

        try:
            relay_host = self.configure_relay(hostname)
        except socket.error:
            logging.exception("Failed to connect to host %s:%d", hostname, self.port)
            raise

        relay_host.sendmail(sender, recipient, str(message))
        relay_host.quit()

    def resolve_relay_host(self, To):
        target_host = To.split("@")[1]

        try:
            mx_host = str(resolver.query(target_host, "mx")[0].exchange)
        except resolver.NoAnswer:
            logging.debug("Domain %r does not have an MX record, using %r instead.", target_host, target_host)
            return target_host

        logging.debug("Delivering to MX record %r for target %r", mx_host, target_host)
        return mx_host


    def __repr__(self):
        """Used in logging and debugging to indicate where this relay goes."""
        return "<Relay to (%s:%d)>" % (self.hostname, self.port)


    def reply(self, original, From, Subject, Body):
        """Calls self.send but with the from and to of the original message reversed."""
        self.send(original.From, From=From, Subject=Subject, Body=Body)

    def send(self, To, From, Subject, Body):
        """
        Does what it says, sends an email.  If you need something more complex
        then look at salmon.mail.MailResponse.
        """
        msg = mail.MailResponse(To=To, From=From, Subject=Subject, Body=Body)
        self.deliver(msg)


class SMTPChannel(smtpd.SMTPChannel):
    """Replaces the standard SMTPChannel with one that rejects more than one recipient"""

    def smtp_RCPT(self, arg):
        if self.__rcpttos:
            # We can't properly handle multiple RCPT TOs in SMTPReceiver
            #
            # SMTP can only return one reply at the end of DATA, making it an
            # all or nothing reply. As we can't roll back a previously
            # successful delivery and the delivery happens without there being
            # a queue, we can end up in a state where one recipient has
            # received their mail and another has not (due to a 550 response
            # raised by the handler). At that point there's no reasonable
            # response to give the client - we haven't delivered everything,
            # but we haven't delivered *nothing* either.
            #
            # So we bug out early and hope for the best. At worst mail will
            # bounce, but nothing will be lost.
            #
            # Of course, if smtpd.SMTPServer or SMTPReceiver implemented a
            # queue and bounces like you're meant too...
            logging.warning("Client attempted to deliver mail with multiple RCPT TOs. This is not supported.")
            self.push("451 Will not accept multiple recipients in one transaction")
        else:
            smtpd.SMTPChannel.smtp_RCPT(self, arg)


class SMTPReceiver(smtpd.SMTPServer):
    """Receives emails and hands it to the Router for further processing."""

    def __init__(self, host='127.0.0.1', port=8825):
        """
        Initializes to bind on the given port and host/ipaddress.  Typically
        in deployment you'd give 0.0.0.0 for "all internet devices" but consult
        your operating system.

        This uses smtpd.SMTPServer in the __init__, which means that you have to
        call this far after you use python-daemonize or else daemonize will
        close the socket.
        """
        self.host = host
        self.port = port
        smtpd.SMTPServer.__init__(self, (self.host, self.port), None)

    def start(self):
        """
        Kicks everything into gear and starts listening on the port.  This
        fires off threads and waits until they are done.
        """
        logging.info("SMTPReceiver started on %s:%d.", self.host, self.port)
        self.poller = threading.Thread(target=asyncore.loop,
                kwargs={'timeout':0.1, 'use_poll':True})
        self.poller.start()

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            conn, addr = pair
            channel = SMTPChannel(self, conn, addr)

    def process_message(self, Peer, From, To, Data):
        """
        Called by smtpd.SMTPServer when there's a message received.
        """

        try:
            logging.debug("Message received from Peer: %r, From: %r, to To %r.", Peer, From, To)
            routing.Router.deliver(mail.MailRequest(Peer, From, To, Data))
        except SMTPError, err:
            # looks like they want to return an error, so send it out
            return str(err)
        except Exception:
            logging.exception("Exception while processing message from Peer: %r, From: %r, to To %r.",
                          Peer, From, To)
            undeliverable_message(Data, "Error in message %r:%r:%r, look in logs." % (Peer, From, To))


    def close(self):
        """Doesn't do anything except log who called this, since nobody should.  Ever."""
        logging.error(traceback.format_exc())


class LMTPReceiver(lmtpd.LMTPServer):
    """Receives emails and hands it to the Router for further processing."""

    def __init__(self, host='127.0.0.1', port=8824, socket=None):
        """
        Initializes to bind on the given port and host/ipaddress. Remember that
        LMTP isn't for use over a WAN, so bind it to either a LAN address or
        localhost. If socket is not None, it will be assumed to be a path name
        and a UNIX socket will be set up instead.

        This uses lmtpd.LMTPServer in the __init__, which means that you have to
        call this far after you use python-daemonize or else daemonize will
        close the socket.
        """
        if socket is None:
            self.socket = "%s:%d" % (host, port)
            lmtpd.LMTPServer.__init__(self, (host, port))
        else:
            self.socket = socket
            lmtpd.LMTPServer.__init__(self, socket)

    def start(self):
        """
        Kicks everything into gear and starts listening on the port.  This
        fires off threads and waits until they are done.
        """
        logging.info("LMTPReceiver started on %s.", self.socket)
        self.poller = threading.Thread(target=asyncore.loop,
                kwargs={'timeout':0.1, 'use_poll':True})
        self.poller.start()

    def process_message(self, Peer, From, To, Data):
        """
        Called by lmtpd.LMTPServer when there's a message received.
        """

        try:
            logging.debug("Message received from Peer: %r, From: %r, to To %r.", Peer, From, To)
            routing.Router.deliver(mail.MailRequest(Peer, From, To, Data))
        except SMTPError, err:
            # looks like they want to return an error, so send it out
            # and yes, you should still use SMTPError in your handlers
            return str(err)
        except Exception:
            logging.exception("Exception while processing message from Peer: %r, From: %r, to To %r.",
                          Peer, From, To)
            undeliverable_message(Data, "Error in message %r:%r:%r, look in logs." % (Peer, From, To))

    def close(self):
        """Doesn't do anything except log who called this, since nobody should.  Ever."""
        logging.error(traceback.format_exc())

class QueueReceiver(object):
    """
    Rather than listen on a socket this will watch a queue directory and
    process messages it recieves from that.  It works in almost the exact
    same way otherwise.
    """

    def __init__(self, queue_dir, sleep=10, size_limit=0, oversize_dir=None):
        """
        The router should be fully configured and ready to work, the
        queue_dir can be a fully qualified path or relative.
        """
        self.queue = queue.Queue(queue_dir, pop_limit=size_limit,
                                 oversize_dir=oversize_dir)
        self.queue_dir = queue_dir
        self.sleep = sleep

    def start(self, one_shot=False):
        """
        Start simply loops indefinitely sleeping and pulling messages
        off for processing when they are available.

        If you give one_shot=True it will run once rather than do a big
        while loop with a sleep.
        """

        logging.info("Queue receiver started on queue dir %s", self.queue_dir)
        logging.debug("Sleeping for %d seconds...", self.sleep)

        inq = queue.Queue(self.queue_dir)

        while True:
            keys = inq.keys()

            for key in keys:
                msg = inq.get(key)

                if msg:
                    logging.debug("Pulled message with key: %r off", key)
                    self.process_message(msg)
                    logging.debug("Removed %r key from queue.", key)

	        inq.remove(key)

            if one_shot:
                return
            else:
                time.sleep(self.sleep)

    def process_message(self, msg):
        """
        Exactly the same as SMTPReceiver.process_message but just designed for the queue's
        quirks.
        """

        try:
            logging.debug("Message received from Peer: %r, From: %r, to To %r.", msg.Peer, msg.From, msg.To)
            routing.Router.deliver(msg)
        except SMTPError, err:
            # looks like they want to return an error, so send it out
            logging.exception("Raising SMTPError when running in a QueueReceiver is unsupported.")
            undeliverable_message(msg.Data, err.message)
        except Exception:
            logging.exception("Exception while processing message from Peer: "
                              "%r, From: %r, to To %r.", msg.Peer, msg.From, msg.To)
            undeliverable_message(msg.Data, "Router failed to catch exception.")
