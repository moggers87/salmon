"""
The majority of the server related things Salmon needs to run, like receivers,
relays, and queue processors.
"""
from functools import partial
from multiprocessing.dummy import Pool
import asyncio
import asyncore
import logging
import smtpd
import smtplib
import threading
import time

from aiosmtpd.controller import Controller
from aiosmtpd.lmtp import LMTP
from aiosmtpd.smtp import SMTP
from dns import resolver
import lmtpd

from salmon import __version__, mail, queue, routing
from salmon.bounce import COMBINED_STATUS_CODES, PRIMARY_STATUS_CODES, SECONDARY_STATUS_CODES

ROUTER_VERSION_STRING = "Salmon Mail router, version %s" % __version__
SMTP_MULTIPLE_RCPTS_ERROR = "451 Will not accept multiple recipients in one transaction"

lmtpd.__version__ = ROUTER_VERSION_STRING
smtpd.__version__ = ROUTER_VERSION_STRING


def undeliverable_message(raw_message, failure_type):
    """
    Used universally in this file to shove totally screwed messages
    into the routing.Router.UNDELIVERABLE_QUEUE (if it's set).
    """
    if routing.Router.UNDELIVERABLE_QUEUE is not None:
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


class Relay:
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

        if ssl and lmtp:
            raise TypeError("LMTP over SSL not supported. Use STARTTLS instead.")
        if ssl and starttls:
            raise TypeError("SSL and STARTTLS make no sense together")

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

        relay_host = self.configure_relay(hostname)
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


def _deliver(receiver, Peer, From, To, Data, **kwargs):
    try:
        logging.debug("Message received from Peer: %r, From: %r, to To %r.", Peer, From, To)
        routing.Router.deliver(mail.MailRequest(Peer, From, To, Data))
    except SMTPError as err:
        # looks like they want to return an error, so send it out
        return str(err)
    except Exception:
        logging.exception("Exception while processing message from Peer: %r, From: %r, to To %r.",
                          Peer, From, To)
        undeliverable_message(Data, "Error in message %r:%r:%r, look in logs." % (Peer, From, To))


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
            self.push(SMTP_MULTIPLE_RCPTS_ERROR)
        else:
            smtpd.SMTPChannel.smtp_RCPT(self, arg)


class SMTPReceiver(smtpd.SMTPServer):
    """Receives emails and hands it to the Router for further processing."""

    def __init__(self, host='127.0.0.1', port=8825):
        """
        Initializes to bind on the given port and host/IP address.  Typically
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
        self.poller = threading.Thread(target=asyncore.loop, kwargs={'timeout': 0.1, 'use_poll': True})
        self.poller.start()

    def stop(self):
        self.close()
        self.poller.join()

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            conn, addr = pair
            SMTPChannel(self, conn, addr)

    def process_message(self, Peer, From, To, Data, **kwargs):
        """
        Called by smtpd.SMTPServer when there's a message received.
        """
        return _deliver(self, Peer, From, To, Data, **kwargs)


class LMTPReceiver(lmtpd.LMTPServer):
    """Receives emails and hands it to the Router for further processing."""

    def __init__(self, host='127.0.0.1', port=8824, socket=None):
        """
        Initializes to bind on the given port and host/IP address. Remember that
        LMTP isn't for use over a WAN, so bind it to either a LAN address or
        localhost. If socket is not None, it will be assumed to be a path name
        and a UNIX socket will be set up instead.

        This uses lmtpd.LMTPServer in the __init__, which means that you have to
        call this far after you use python-daemonize or else daemonize will
        close the socket.
        """
        if socket is None:
            self.host = host
            self.port = port
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
        self.poller = threading.Thread(target=asyncore.loop, kwargs={'timeout': 0.1, 'use_poll': True})
        self.poller.start()

    def stop(self):
        self.close()
        self.poller.join()

    def process_message(self, Peer, From, To, Data, **kwargs):
        """
        Called by lmtpd.LMTPServer when there's a message received.
        """
        return _deliver(self, Peer, From, To, Data, **kwargs)


class SMTPOnlyOneRcpt(SMTP):
    async def smtp_RCPT(self, arg):
        if self.envelope.rcpt_tos:
            await self.push(SMTP_MULTIPLE_RCPTS_ERROR)
        else:
            await super().smtp_RCPT(arg)


class SMTPHandler:
    def __init__(self, executor=None):
        self.executor = executor

    async def handle_DATA(self, server, session, envelope):
        status = await server.loop.run_in_executor(self.executor, partial(
            _deliver,
            self,
            session.peer,
            envelope.mail_from,
            envelope.rcpt_tos[0],
            envelope.content,
        ))
        return status or "250 Ok"


class AsyncSMTPReceiver(Controller):
    """Receives emails and hands it to the Router for further processing."""
    def __init__(self, handler=None, **kwargs):
        if handler is None:
            handler = SMTPHandler()
        super().__init__(handler, **kwargs)

    def factory(self):
        # TODO implement a queue
        return SMTPOnlyOneRcpt(self.handler, enable_SMTPUTF8=self.enable_SMTPUTF8, ident=ROUTER_VERSION_STRING)


class LMTPHandler:
    def __init__(self, executor=None):
        self.executor = executor

    async def handle_DATA(self, server, session, envelope):
        statuses = []
        for rcpt in envelope.rcpt_tos:
            status = await server.loop.run_in_executor(self.executor, partial(
                _deliver,
                self,
                session.peer,
                envelope.mail_from,
                rcpt, envelope.content,
            ))
            statuses.append(status or "250 Ok")
        return "\r\n".join(statuses)


class AsyncLMTPReceiver(Controller):
    """Receives emails and hands it to the Router for further processing."""
    def __init__(self, handler=None, *, socket=None, **kwargs):
        if handler is None:
            handler = LMTPHandler()
        self.socket_path = socket
        super().__init__(handler, **kwargs)

    def factory(self):
        return LMTP(self.handler, enable_SMTPUTF8=self.enable_SMTPUTF8, ident=ROUTER_VERSION_STRING)

    def _run(self, ready_event):
        # adapted from aiosmtpd.controller.Controller._run
        # from commit 97730f37f4a283b3da3fa3dbf30dd925695fea69
        # Copyright 2015-2017 The aiosmtpd developers
        # aiosmtpd is released under the Apache License version 2.0.
        asyncio.set_event_loop(self.loop)
        try:
            if self.socket_path is None:
                server = self.loop.create_server(self.factory, host=self.hostname,
                                                 port=self.port, ssl=self.ssl_context)
            else:
                # no ssl on unix sockets, it doesn't really make sense
                server = self.loop.create_unix_server(self.factory, path=self.socket_path)
            self.server = self.loop.run_until_complete(server)
        except Exception as error:
            self._thread_exception = error
            return
        self.loop.call_soon(ready_event.set)
        self.loop.run_forever()
        self.server.close()
        self.loop.run_until_complete(self.server.wait_closed())
        self.loop.close()
        self.server = None


class QueueReceiver:
    """
    Rather than listen on a socket this will watch a queue directory and
    process messages it receives from that.  It works in almost the exact
    same way otherwise.
    """

    def __init__(self, queue_dir, sleep=10, size_limit=0, oversize_dir=None, workers=10):
        """
        The router should be fully configured and ready to work, the queue_dir
        can be a fully qualified path or relative. The option workers dictates
        how many threads are started to process messages. Consider adding
        ``@nolocking`` to your handlers if you are able to.
        """
        self.queue = queue.Queue(queue_dir, pop_limit=size_limit,
                                 oversize_dir=oversize_dir)
        self.sleep = sleep

        # Pool is from multiprocess.dummy which uses threads rather than processes
        self.workers = Pool(workers)

    def start(self, one_shot=False):
        """
        Start simply loops indefinitely sleeping and pulling messages
        off for processing when they are available.

        If you give one_shot=True it will stop once it has exhausted the queue
        """

        logging.info("Queue receiver started on queue dir %s", self.queue.dir)
        logging.debug("Sleeping for %d seconds...", self.sleep)

        # if there are no messages left in the maildir and this a one-shot, the
        # while loop terminates
        while not (len(self.queue) == 0 and one_shot):
            # if there's nothing in the queue, take a break
            if len(self.queue) == 0:
                time.sleep(self.sleep)
                continue

            try:
                key, msg = self.queue.pop()
            except KeyError:
                logging.debug("Could not find message in Queue")
                continue

            logging.debug("Pulled message with key: %r off", key)
            self.workers.apply_async(self.process_message, args=(msg,))

        self.workers.close()
        self.workers.join()

    def process_message(self, msg):
        """
        Exactly the same as SMTPReceiver.process_message but just designed for the queue's
        quirks.
        """

        try:
            logging.debug("Message received from Peer: %r, From: %r, to To %r.", msg.Peer, msg.From, msg.To)
            routing.Router.deliver(msg)
        except SMTPError as err:
            logging.exception("Raising SMTPError when running in a QueueReceiver is unsupported.")
            undeliverable_message(msg.Data, err.message)
        except Exception:
            logging.exception("Exception while processing message from Peer: "
                              "%r, From: %r, to To %r.", msg.Peer, msg.From, msg.To)
            undeliverable_message(msg.Data, "Router failed to catch exception.")
