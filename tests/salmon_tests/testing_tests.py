import os

from mock import Mock, patch
from nose.tools import with_setup

from salmon.testing import (
    RouterConversation,
    assert_in_state,
    clear_queue,
    delivered,
    queue,
    relay,
    spelling,
)

from .setup_env import setup_salmon_dirs, teardown_salmon_dirs


relay = relay(port=8899)


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
def test_clear_queue():
    queue().push("Test")
    assert queue().count() > 0

    clear_queue()
    assert queue().count() == 0


@patch("smtplib.SMTP")
@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
def test_relay(smtp_mock):
    smtp_mock.return_value = Mock()

    relay.send('test@localhost', 'zedshaw@localhost', 'Test message', 'Test body')

    assert smtp_mock.return_value.sendmail.called
    assert smtp_mock.return_value.quit.called


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
def test_delivered():
    clear_queue()
    queue().push("To: gooduser@localhost\nFrom: tester@localhost\n\nHi\n")

    assert delivered("gooduser@localhost"), "Test message not delivered."
    assert not delivered("baduser@localhost")
    assert_in_state('salmon_tests.handlers.simple_fsm_mod', 'gooduser@localhost', 'tester@localhost', 'START')


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
def test_RouterConversation():
    client = RouterConversation('tester@localhost', 'Test router conversations.')
    client.begin()
    client.say('testlist@localhost', 'This is a test')
    delivered('testlist@localhost'), "Test message not delivered."


def test_spelling():
    # specific to a mac setup, because macs are lame
    if 'PYENCHANT_LIBRARY_PATH' not in os.environ:
        os.environ['PYENCHANT_LIBRARY_PATH'] = '/opt/local/lib/libenchant.dylib'

    template = "tests/salmon_tests/templates/template.txt"
    contents = open(template).read()
    assert spelling(template, contents)
