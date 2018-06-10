# This file contains python variables that configure Salmon for email processing.
relay_config = {'host': 'localhost', 'port': 8825}

receiver_config = {'host': 'localhost', 'port': 8823}

handlers = []

dump_handlers = ["test_handlers.dump"]

router_defaults = {'host': 'localhost'}

template_config = {'dir': 'salmon_tests', 'module': '.'}

# this is for when you run the config.queue boot
queue_config = {'queue': 'run/deferred', 'sleep': 10}

queue_handlers = []

QUEUE_PATH = "run/dump"
UNDELIVERABLE_QUEUE = "run/undeliverable"
