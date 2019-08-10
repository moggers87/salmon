from __future__ import print_function

from shutil import rmtree
from unittest import TestCase
import os

from salmon.routing import Router

dirs = ("run", "logs")


def setup_router(handlers):
    Router.clear_routes()
    Router.clear_states()
    Router.HANDLERS.clear()
    Router.load(handlers)
    Router.reload()


def clean_dirs():
    for path in dirs:
        rmtree(path, ignore_errors=True)


class SalmonTestCase(TestCase):
    def setUp(self):
        clean_dirs()
        for path in dirs:
            os.mkdir(path)
        self.addCleanup(clean_dirs)
