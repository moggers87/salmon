import logging
import logging.config

from salmon import queue
from salmon.routing import Router
from salmon.server import SMTPReceiver

from config import settings

logging.config.fileConfig("tests/config/logging.conf")

settings.receiver = SMTPReceiver(**settings.receiver_config)

Router.defaults(**settings.router_defaults)
Router.load(settings.dump_handlers)
Router.RELOAD = True
Router.UNDELIVERABLE_QUEUE = queue.Queue(settings.UNDELIVERABLE_QUEUE)
