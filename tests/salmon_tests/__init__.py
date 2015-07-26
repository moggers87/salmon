import os
import shutil

import config.testing  # noqa


dirs = ["run", "logs"]


def setup_package():
    for path in dirs:
        os.mkdir(path)


def teardown_package():
    for path in dirs:
        shutil.rmtree(path, ignore_errors=True)
