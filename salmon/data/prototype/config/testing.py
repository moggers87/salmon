import logging.config

from salmon.routing import Router
from salmon.server import Relay

from . import settings

logging.config.fileConfig("config/test_logging.conf")

# the relay host to actually send the final message to (set debug=1 to see what
# the relay is saying to the log server).
settings.relay = Relay(host=settings.relay_config['host'],
                       port=settings.relay_config['port'], debug=0)


settings.receiver = None

Router.defaults(**settings.router_defaults)
Router.load(settings.handlers)
Router.RELOAD = True
Router.LOG_EXCEPTIONS = False
