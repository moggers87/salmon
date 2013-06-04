from nose.tools import *
from salmon.routing import Router
from salmon_tests import message_tests
import salmon.handlers.log
import salmon.handlers.queue

def test_log_handler():
    Router.deliver(message_tests.test_mail_request())

def test_queue_handler():
    Router.deliver(message_tests.test_mail_request())
