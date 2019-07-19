from __future__ import print_function

from shutil import rmtree
from unittest import TestCase
import os

from salmon.routing import Router

dirs = ["run", "logs"]


def setup_router(handlers):
    Router.clear_routes()
    Router.clear_states()
    Router.HANDLERS.clear()
    Router.load(handlers)
    Router.reload()


class SalmonTestCase(TestCase):
    def setUp(self):
        for path in dirs:
            rmtree(path, ignore_errors=True)
            os.mkdir(path)

    def tearDown(self):
        for path in dirs:
            rmtree(path, ignore_errors=True)
