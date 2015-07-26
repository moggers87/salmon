import os
from shutil import rmtree

from salmon.routing import Router

from . import dirs


def clear_dir(dir_path):
    for dir_item in os.listdir(dir_path):
        print dir_item
        full_path = '%s/%s' % (dir_path, dir_item)
        print full_path
        if os.path.isfile(full_path):
            os.unlink(full_path)
        else:
            rmtree(full_path)


def setup_salmon_dirs():
    for path in dirs:
        clear_dir(path)


def teardown_salmon_dirs():
    for path in dirs:
        clear_dir(path)


def setup_router(handlers):
    Router.clear_routes()
    Router.clear_states()
    Router.HANDLERS.clear()
    Router.load(handlers)
