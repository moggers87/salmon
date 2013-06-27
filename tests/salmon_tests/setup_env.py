from os import makedirs
from shutil import rmtree

dirs = ["run", "logs"]

def setup_salmon_dirs():
    for path in dirs:
        makedirs(path)

def teardown_salmon_dirs():
    for path in dirs:
        rmtree(path)
