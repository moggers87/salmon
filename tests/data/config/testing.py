# Fake boot module for tests
from salmon.routing import Router

Router.defaults(host="localhost")
Router.load([])
Router.RELOAD = False
Router.LOG_EXCEPTIONS = False
