from salmon import queue
from salmon.routing import nolocking, route, stateless
from salmon.utils import settings


@route("(to)@(host)", to=".+", host="example.com")
@stateless
@nolocking
def START(message, to=None, host=None):
    inbox = queue.Queue(settings.QUEUE_PATH)
    inbox.push(message)
