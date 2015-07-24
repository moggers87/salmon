from salmon import commands, utils, mail, routing, encoding
from salmon.testing import spelling
from setup_env import setup_salmon_dirs, teardown_salmon_dirs

from mock import *
from nose.tools import *
import imp
import os
import shutil
import sys


def setup():
    if os.path.exists("run/fake.pid"):
        os.unlink("run/fake.pid")

def teardown():
    if os.path.exists("run/fake.pid"):
        os.unlink("run/fake.pid")

def make_fake_pid_file():
    f = open("run/fake.pid","w")
    f.write("0")
    f.close()


def get_command(command):
    mock_parser = Mock()
    command(mock_parser)
    func = mock_parser.set_defaults.call_args[1]["func"]

    return func


def test_send_command():
    command = get_command(commands.send_command)
    command(sender='test@localhost', to='test@localhost', body='Test body', subject='Test subject', attach='setup.py', port=8899, host="127.0.0.1")


def test_status_command():
    command = get_command(commands.status_command)
    command(pid='run/log.pid')
    command(pid='run/donotexist.pid')

@patch('sys.argv', ['salmon'])
@raises(SystemExit)
def test_main():
    commands.main()


@patch('salmon.queue.Queue')
@patch('sys.exit', new=Mock())
def test_queue_command(MockQueue):
    mq = MockQueue()
    mq.get.return_value = "A sample message"
    mq.keys.return_value = ["key1","key2"]
    mq.pop.return_value = ('key1', 'message1')
    mq.count.return_value = 1

    command = get_command(commands.queue_command)
    
    command("run/queue", pop=True)
    assert mq.pop.called
    
    command("run/queue", get='somekey')
    assert mq.get.called
    
    command("run/queue", remove='somekey')
    assert mq.remove.called
    
    command("run/queue", clear=True)
    assert mq.clear.called
    
    command("run/queue", keys=True)
    assert mq.keys.called

    command("run/queue", count=True)
    assert mq.count.called


@patch('sys.exit', new=Mock())
def test_gen_command():
    command = get_command(commands.gen_command)
    project = 'tests/testproject'
    if os.path.exists(project):
        shutil.rmtree(project)

    command(project=project)
    assert os.path.exists(project)

    # test that it exits if the project exists
    command(project=project)
    assert sys.exit.called

    sys.exit.reset_mock()
    command(project=project, force=True)
    assert not sys.exit.called

    shutil.rmtree(project)


def test_routes_command():
    command = get_command(commands.routes_command)
    command(['salmon.handlers.log', 'salmon.handlers.queue'])

    # test with the -test option
    command(['salmon.handlers.log', 'salmon.handlers.queue'], test="anything@localhost")

    # test with the -test option but no matches
    routing.Router.clear_routes()
    command([], test="anything@localhost")


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
@patch('sys.exit', new=Mock())
@patch('salmon.utils.daemonize', new=Mock())
@patch('salmon.server.SMTPReceiver')
def test_log_command(MockSMTPReceiver):
    command = get_command(commands.log_command)
    ms = MockSMTPReceiver()
    ms.start.function()

    setup()  # make sure it's clear for fake.pid
    command(host="127.0.0.1", port=8825, chdir=".", pid="run/fake.pid")
    assert utils.daemonize.called
    assert ms.start.called

    # test that it exits on existing pid
    make_fake_pid_file()
    command(host="127.0.0.1", port=8825, chdir=".", pid="run/fake.pid")
    assert sys.exit.called


@patch('sys.stdin', new=Mock())
def test_sendmail_command():
    sys.stdin.read.function()

    msg = mail.MailResponse(To="tests@localhost", From="tests@localhost",
                            Subject="Hello", Body="Test body.")
    sys.stdin.read.return_value = str(msg)

    command = get_command(commands.sendmail_command)
    command(host="127.0.0.1", port=8899, recipients=["test@localhost"])


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
@patch('sys.exit', new=Mock())
@patch('salmon.utils.daemonize', new=Mock())
@patch('salmon.utils.import_settings', new=Mock())
@patch('salmon.utils.drop_priv', new=Mock())
@patch('sys.path', new=Mock())
def test_start_command():
    # normal start
    command = get_command(commands.start_command)
    command(pid="smtp.pid", force=False, chdir=".", boot="config.boot")
    assert utils.daemonize.call_count == 1
    assert utils.import_settings.called

    # start with pid file existing already
    make_fake_pid_file()
    command(pid="run/fake.pid", force=False, chdir=".", boot="config.boot")
    assert sys.exit.called

    # start with pid file existing and force given
    assert os.path.exists("run/fake.pid")
    command(boot="config.boot", chdir=".", force=True, pid="run/fake.pid")
    assert not os.path.exists("run/fake.pid")

    # start with a uid but no gid
    command(boot="config.boot", chdir=".", uid=1000, gid=False, pid="run/fake.pid", force=True)
    assert not utils.drop_priv.called

    # start with a uid/gid given that's valid
    command(boot="config.boot", chdir=".", uid=1000, gid=1000, pid="run/fake.pid", force=True)
    assert utils.drop_priv.called

    # non daemon start
    daemonize_call_count = utils.daemonize.call_count
    command(boot="config.boot", chdir=".", pid="run/fake.pid", daemon=False, force=True)
    assert utils.daemonize.call_count == daemonize_call_count  # same count -> not called


def raise_OSError(*x, **kw):
    raise OSError('Fail')


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
@patch('sys.exit', new=Mock())
@patch('os.kill', new=Mock())
@patch('glob.glob', new=lambda x: ['run/fake.pid'])
def test_stop_command():
    command = get_command(commands.stop_command)
    # gave a bad pid file
    try:
        command(pid="run/dontexit.pid")
    except IOError:
        assert sys.exit.called

    make_fake_pid_file()
    command(pid="run/fake.pid")

    make_fake_pid_file()
    command(pid="", all="run")

    make_fake_pid_file()
    command(pid="run/fake.pid", kill=True)
    assert os.kill.called
    assert not os.path.exists("run/fake.pid")

    make_fake_pid_file()
    os.kill.side_effect = raise_OSError
    command(pid="run/fake.pid", kill=True)


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
def test_cleanse_command():
    command = get_command(commands.cleanse_command)
    command(input='run/queue', output='run/cleansed')
    assert os.path.exists('run/cleansed')


def raises_EncodingError(*args):
    raise encoding.EncodingError


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
@patch('salmon.encoding.from_message')
def test_cleans_command_with_encoding_error(from_message):
    command = get_command(commands.cleanse_command)
    from_message.side_effect = raises_EncodingError
    command(input='run/queue', output='run/cleansed')


@with_setup(setup_salmon_dirs, teardown_salmon_dirs)
def test_blast_command():
    command = get_command(commands.blast_command)
    command(input='run/queue', host="127.0.0.1", port=8899)
