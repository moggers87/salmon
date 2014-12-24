"""
This module contains various decorators used by handlers.

MailRequestEncoder and EmailEncoder are probably the most useful. They
convert incoming mail data into something usable by Python.
"""
import email


from salmon.mail import MailRequest


class MailRequestEncoder(object):
    """
    Overwrites the IncomingMessage object with a traditional Salmon
    MailRequest object.
    """
    def __init__(self, func):
        self.func = func

    def __call__(self, message, **kwargs):
        request = MailRequest(message.Peer, message.From, messaage.To, message.Data)
        return self.func(request, **kwargs)

class EmailEncoder(object):
    """
    Attaches a Python Email object to message.Email
    """
    def __init__(self, func):
        self.func = func

    def __call__(self, message, **kwargs):
        message.Email = email.message_from_string(message.Data)
        return self.func(message, **kwargs)
