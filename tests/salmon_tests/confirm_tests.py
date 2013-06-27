from nose.tools import *
import shutil
import os

from setup_env import setup_salmon_dirs, teardown_salmon_dirs
from salmon.confirm import *
from salmon.testing import *
from salmon import mail, queue

def setup_module(module):
    setup_salmon_dirs()
    module.storage = ConfirmationStorage()
    module.engine = ConfirmationEngine('run/confirm', storage)

def teardown_module(module):
    teardown_salmon_dirs()

def test_ConfirmationStorage():
    storage.store('testing', 'somedude@localhost',
                  '12345', '567890')
    secret, pending_id = storage.get('testing', 'somedude@localhost')
    assert_equal(secret, '12345')
    assert_equal(pending_id, '567890')

    storage.delete('testing', 'somedude@localhost')
    assert_equal(len(storage.confirmations), 0)

    storage.store('testing', 'somedude@localhost',
                  '12345', '567890')
    assert_equal(len(storage.confirmations), 1)
    storage.clear()
    assert_equal(len(storage.confirmations), 0)


def test_ConfirmationEngine_send():
    queue.Queue('run/queue').clear()
    engine.clear()

    list_name = 'testing'
    action = 'subscribing to'
    host = 'localhost'

    message = mail.MailRequest('fakepeer', 'somedude@localhost',
                               'testing-subscribe@localhost', 'Fake body.')

    engine.send(relay(port=8899), 'testing', message, 'confirmation.msg', locals())
   
    confirm = delivered('confirm')
    assert delivered('somedude', to_queue=engine.pending)
    assert confirm

    return confirm

def test_ConfirmationEngine_verify():
    confirm = test_ConfirmationEngine_send()

    resp = mail.MailRequest('fakepeer', '"Somedude Smith" <somedude@localhost>',
                           confirm['Reply-To'], 'Fake body')

    target, _, expect_secret = confirm['Reply-To'].split('-')
    expect_secret = expect_secret.split('@')[0]

    found = engine.verify(target, resp['from'], 'invalid_secret')
    assert not found

    pending = engine.verify(target, resp['from'], expect_secret)
    assert pending, "Verify failed: %r not in %r." % (expect_secret,
                                                      storage.confirmations)

    assert_equal(pending['from'], 'somedude@localhost')
    assert_equal(pending['to'], 'testing-subscribe@localhost')


def test_ConfirmationEngine_cancel():
    confirm = test_ConfirmationEngine_send()

    target, _, expect_secret = confirm['Reply-To'].split('-')
    expect_secret = expect_secret.split('@')[0]

    engine.cancel(target, confirm['To'], expect_secret)
    
    found = engine.verify(target, confirm['To'], expect_secret)
    assert not found
