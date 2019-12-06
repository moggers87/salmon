from shutil import rmtree
import os
import smtplib
import subprocess
import sys
import time

from salmon import queue

from .setup_env import SalmonTestCase, dirs
from test_app.config import settings as server_settings


class IntegrationTestCase(SalmonTestCase):
    @classmethod
    def setUpClass(cls):
        cls._cwd = "tests/data/test_app"
        for path in dirs:
            rmtree(os.path.join(cls._cwd, path), ignore_errors=True)
            os.mkdir(os.path.join(cls._cwd, path))
        cls._server = subprocess.Popen(["salmon", "start", "--boot", "config.dump", "--no-daemon"],
                                       cwd=cls._cwd, stdout=sys.stdout, stderr=sys.stderr)
        for i in range(5):
            try:
                conn = smtplib.SMTP(**server_settings.receiver_config)
            except Exception:
                time.sleep(2**i)
                continue
            else:
                conn.quit()
                return

        raise Exception("Server still not ready, something must be wrong")

    @classmethod
    def tearDownClass(cls):
        cls._server.kill()
        cls._server = None
        for path in dirs:
            rmtree(os.path.join(cls._cwd, path), ignore_errors=True)

    def setUp(self):
        super(IntegrationTestCase, self).setUp()
        # re-create destoryed queues
        queue.Queue(os.path.join(self._cwd, server_settings.UNDELIVERABLE_QUEUE)).clear()
        queue.Queue(os.path.join(self._cwd, server_settings.QUEUE_PATH)).clear()

    def test_we_get_message(self):
        client = smtplib.SMTP(**server_settings.receiver_config)

        client.helo()
        client.sendmail("me@example.com", "you@example.com", "hello")

        undelivered = queue.Queue(os.path.join(self._cwd, server_settings.UNDELIVERABLE_QUEUE))
        self.assertEqual(len(undelivered), 0)

        inbox = queue.Queue(os.path.join(self._cwd, server_settings.QUEUE_PATH))
        self.assertEqual(len(inbox), 1)

    def test_we_dont_get_message(self):
        client = smtplib.SMTP(**server_settings.receiver_config)

        client.helo()
        client.sendmail("me@example.com", "you@example1.com", "hello")

        undelivered = queue.Queue(os.path.join(self._cwd, server_settings.UNDELIVERABLE_QUEUE))
        self.assertEqual(len(undelivered), 1)

        inbox = queue.Queue(os.path.join(self._cwd, server_settings.QUEUE_PATH))
        self.assertEqual(len(inbox), 0)
