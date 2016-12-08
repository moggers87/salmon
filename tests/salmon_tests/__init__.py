import os
import shutil
import subprocess
import time

import config.testing  # noqa


dirs = ["run", "logs"]
DUMMY_RELAY=None


def setup_package():
    for path in dirs:
        os.mkdir(path)
    DUMMY_RELAY=subprocess.Popen("python -m smtpd -n -c DebuggingServer localhost:7899 > logs/smtpd.log", shell=True)
    time.sleep(10)


def teardown_package():
    for path in dirs:
        shutil.rmtree(path, ignore_errors=True)
    if DUMMY_RELAY:
        DUMMY_RELAY.send_signal(9)
