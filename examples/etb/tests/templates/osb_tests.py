from nose.tools import *
from salmon.testing import *
from salmon import view
import os
from glob import glob

def test_spelling():
    message = {}
    original = {}
    for path in glob("app/templates/mail/*.msg"):
        template = "mail/" + os.path.basename(path)
        result = view.render(locals(), template)
        spelling(template, result)

