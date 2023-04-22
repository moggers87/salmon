from salmon import queue
from salmon.routing import route, stateless
from salmon.utils import settings


@route("(to)@(host)", to=".+", host="example.com")
@stateless
def START(message, to=None, host=None):
    inbox = queue.Queue(settings.QUEUE_PATH)
    inbox.push(message)
