from setup_env import setup_salmon_dirs, teardown_salmon_dirs, setup_router
from salmon.testing import *

from nose.tools import *
import os

relay = relay(port=8899)


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
def test_clear_queue():
    queue().push("Test")
    assert queue().count() > 0

    clear_queue()
    assert queue().count() == 0

@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
def test_relay():
    clear_queue()
    relay.send('test@localhost', 'zedshaw@localhost', 'Test message', 'Test body')
    assert queue().keys()

@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
def test_delivered():
    clear_queue()

    relay.send("zedshaw@localhost", "tester@localhost", Subject="Test subject.", Body="Test body.")
    assert delivered("zedshaw@localhost"), "Test message not delivered."
    assert not delivered("badman@localhost")
    assert_in_state('salmon_tests.handlers.simple_fsm_mod', 'zedshaw@localhost', 'tester@localhost', 'START')

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
