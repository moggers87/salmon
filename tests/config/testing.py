import logging
import logging.config

from config import settings
from salmon import view
from salmon.routing import Router
from salmon.server import Relay

import jinja2

# configure logging to go to a log file
logging.config.fileConfig("tests/config/logging.conf")

# the relay host to actually send the final message to (set debug=1 to see what
# the relay is saying to the log server).
settings.relay = Relay(host=settings.relay_config['host'],
                       port=settings.relay_config['port'], debug=0)


settings.receiver = None

Router.defaults(**settings.router_defaults)
Router.load(settings.handlers + settings.queue_handlers)
Router.RELOAD = False
Router.LOG_EXCEPTIONS = False

view.LOADER = jinja2.Environment(loader=jinja2.PackageLoader('salmon_tests', 'templates'))
