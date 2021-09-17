"""
The meat of Salmon, doing all the work that actually takes an email and makes
sure that your code gets it.

The three most important parts for a programmer are the Router variable, the
StateStorage base class, and the @route, @route_like, and @stateless decorators.

The salmon.routing.Router variable (it's not a class, just named like one) is
how the whole system gets to the Router.  It is an instance of RoutingBase and
there's usually only one.

The salmon.routing.StateStorage is what you need to implement if you want
Salmon to store the state in a different way.  By default the
salmon.routing.Router object just uses a default MemoryStorage to do its job.
If you want to use a custom storage, then in your boot modiule you would set
salmon.routing.Router.STATE_STORE to what you want to use.

Finally, when you write a state handler, it has functions that act as state
functions for dealing with each state.  To tell the Router what function should
handle what email you use a @route decorator.  To tell the Route that one
function routes the same as another use @route_like.  In the case where a state
function should run on every matching email, just use the @stateless decorator
after a @route or @route_like.

If at any time you need to debug your routing setup just use the salmon routes
command.

Routing Control
===============

To control routing there are a set of decorators that you apply to your
functions.

* @route -- The main routing function that determines what addresses you are
  interested in.
* @route_like -- Says that this function routes like another one.
* @stateless -- Indicates this function always runs on each route encountered, and
  no state is maintained.
* @locking -- Use this if you want this handler to be run one call at a time.
* @state_key_generator -- Used on a function that knows how to make your state
  keys for the module, for example if module_name + message.To is needed to maintain
  state.

It's best to put @route or @route_like as the first decorator, then the others
after that.

The @state_key_generator is different since it's not intended to go on a handler
but instead on a simple function, so it shouldn't be combined with the others.
"""
from functools import wraps
from importlib import reload
import logging
import re
import shelve
import sys
import threading
import warnings

ROUTE_FIRST_STATE = 'START'
LOG = logging.getLogger("routing")
SALMON_SETTINGS_VARIABLE_NAME = "_salmon_settings"
_DEFAULT_VALUE = object()


def DEFAULT_STATE_KEY(mod, msg):
    return mod


class StateStorage:
    """
    The base storage class you need to implement for a custom storage
    system.
    """
    def get(self, key, sender):
        """
        You must implement this so that it returns a single string
        of either the state for this combination of arguments, OR
        the ROUTE_FIRST_STATE setting.
        """
        raise NotImplementedError("You have to implement a StateStorage.get.")

    def set(self, key, sender, state):
        """
        Set should take the given parameters and consistently set the state for
        that combination such that when StateStorage.get is called it gives back
        the same setting.
        """
        raise NotImplementedError("You have to implement a StateStorage.set.")

    def clear(self):
        """
        This should clear ALL states, it is only used in unit testing, so you
        can have it raise an exception if you want to make this safer.
        """
        raise NotImplementedError("You have to implement a StateStorage.clear for unit testing to work.")


class MemoryStorage(StateStorage):
    """
    The default simplified storage for the Router to hold the states.  This
    should only be used in testing, as you'll lose all your contacts and their
    states if your server shuts down.
    """
    def __init__(self):
        self.states = {}
        self.lock = threading.RLock()

    def get(self, key, sender):
        key = self.key(key, sender)
        try:
            return self.states[key]
        except KeyError:
            return ROUTE_FIRST_STATE

    def set(self, key, sender, state):
        with self.lock:
            key = self.key(key, sender)
            if state == ROUTE_FIRST_STATE:
                try:
                    del self.states[key]
                except KeyError:
                    pass
            else:
                self.states[key] = state

    def key(self, key, sender):
        return repr([key, sender])

    def clear(self):
        self.states.clear()


class ShelveStorage(MemoryStorage):
    """
    Uses Python's shelve to store the state of the Routers to disk rather than
    in memory like with MemoryStorage.  This will get you going on a small
    install if you need to persist your states (most likely), but if you
    have a database, you'll need to write your own StateStorage that
    uses your ORM or database to store.  Consider this an example.

    NOTE: Because of shelve limitations you can only use ASCII encoded keys.
    """
    def __init__(self, database_path):
        """Database path depends on the backing library use by Python's shelve."""
        super().__init__()
        self.database_path = database_path

    def get(self, key, sender):
        """
        This will lock the internal thread lock, and then retrieve from the
        shelf whatever key you request.  If the key is not found then it
        will set (atomically) to ROUTE_FIRST_STATE.
        """
        with self.lock:
            self.states = shelve.open(self.database_path)
            value = super().get(key.encode('ascii'), sender)
            self.states.close()
            return value

    def set(self, key, sender, state):
        """
        Acquires the self.lock and then sets the requested state in the shelf.
        """
        with self.lock:
            self.states = shelve.open(self.database_path)
            super().set(key.encode('ascii'), sender, state)
            self.states.close()

    def clear(self):
        """
        Primarily used in the debugging/unit testing process to make sure the
        states are clear.  In production this could be a bad thing.
        """
        with self.lock:
            self.states = shelve.open(self.database_path)
            super().clear()
            self.states.close()


class RoutingBase:
    """
    The self is a globally accessible class that is actually more like a
    glorified module.  It is used mostly internally by the salmon.routing
    decorators (route, route_like, stateless) to control the routing
    mechanism.

    It keeps track of the registered routes, their attached functions, the
    order that these routes should be evaluated, any default routing captures,
    and uses the MemoryStorage by default to keep track of the states.

    You can change the storage to another implementation by simple setting:

        Router.STATE_STORE = OtherStorage()

    in your settings module.

    RoutingBase assumes that both your STATE_STORE and handlers are
    thread-safe. For handlers that cannot be made thread-safe, use @locking and
    RoutingBase will use locks to make sure that handler is only called one
    call at a time. Please note that this will have a negative impact on
    performance.

    NOTE: See @state_key_generator for a way to change what the key is to
    STATE_STORE for different state control options.
    """

    def __init__(self):
        self.REGISTERED = {}
        self.ORDER = []
        self.DEFAULT_CAPTURES = {}
        self.STATE_STORE = MemoryStorage()
        self.HANDLERS = {}
        self.RELOAD = False
        self.LOG_EXCEPTIONS = True
        self.UNDELIVERABLE_QUEUE = None
        self.lock = threading.RLock()
        self.call_lock = threading.RLock()

    def register_route(self, format, func):
        """
        Registers this function func into the routes mapping based on the
        format given.  Format should be a regex string ready to be handed to
        re.compile.
        """
        with self.lock:
            if format in self.REGISTERED:
                self.REGISTERED[format][1].append(func)
            else:
                self.ORDER.append(format)
                self.REGISTERED[format] = (re.compile(format, re.IGNORECASE), [func])

    def match(self, address):
        """
        This is a generator that goes through all the routes and
        yields each match it finds.  It expects you to give it a
        blah@blah.com address, NOT "Joe Blow" <blah@blah.com>.
        """
        for format in self.ORDER:
            regex, functions = self.REGISTERED[format]
            match = regex.match(address)
            if match:
                yield functions, match.groupdict()

    def defaults(self, **captures):
        """
        Updates the defaults for routing captures with the given settings.

        You use this in your handlers or your settings module to set
        common regular expressions you'll have in your @route decorators.
        This saves you typing, but also makes it easy to reconfigure later.

        For example, many times you'll have a single host="..." regex
        for all your application's routes.  Put this in your settings.py
        file using route_defaults={'host': '...'} and you're done.
        """
        with self.lock:
            self.DEFAULT_CAPTURES.update(captures)

    def get_state(self, module_name, message):
        """Returns the state that this module is in for the given message (using its from)."""
        key = self.state_key(module_name, message)
        return self.STATE_STORE.get(key, message.From)

    def in_state(self, func, message):
        """
        Determines if this function is in the state for the to/from in the
        message.  Doesn't apply to @stateless state handlers.
        """
        state = self.get_state(func.__module__, message)
        return state and state == func.__name__

    def in_error(self, func, message):
        """
        Determines if the this function is in the 'ERROR' state,
        which is a special state that self puts handlers in that throw
        an exception.
        """
        state = self.get_state(func.__module__, message)
        return state and state == 'ERROR'

    def state_key(self, module_name, message):
        """
        Given a module_name we need to get a state key for, and a
        message that has information to make the key, this function
        calls any registered @state_key_generator and returns that
        as the key.  If none is given then it just returns module_name
        as the key.
        """
        key_func = self.HANDLERS.get(module_name, DEFAULT_STATE_KEY)
        return key_func(module_name, message)

    def set_state(self, module_name, message, state):
        """
        Sets the state of the given module (a string) according to the message to the requested
        state (a string).  This is also how you can force another FSM to a required state.
        """
        key = self.state_key(module_name, message)
        self.STATE_STORE.set(key, message.From, state)

    def _collect_matches(self, message):
        in_state_found = False

        for functions, matchkw in self.match(message.To):
            for func in functions:
                if salmon_setting(func, 'stateless'):
                    yield func, matchkw
                elif not in_state_found and self.in_state(func, message):
                    in_state_found = True
                    yield func, matchkw

    def _enqueue_undeliverable(self, message):
        if self.UNDELIVERABLE_QUEUE is not None:
            LOG.debug("Message to %r from %r undeliverable, putting in undeliverable queue (# of recipients: %d).",
                      message.To, message.From, len(message.To))
            self.UNDELIVERABLE_QUEUE.push(message)
        else:
            LOG.debug("Message to %r from %r didn't match any handlers. (# recipients: %d)",
                      message.To, message.From, len(message.To))

    def deliver(self, message):
        """
        The meat of the whole Salmon operation, this method takes all the
        arguments given, and then goes through the routing listing to figure out
        which state handlers should get the gear.  The routing operates on a
        simple set of rules:

            1) Match on all functions that match the given To in their
            registered format pattern.
            2) Call all @stateless state handlers functions.
            3) Call the first method that's in the right state for the From/To.

        It will log which handlers are being run, and you can use the 'salmon route'
        command to inspect and debug routing problems.

        If you have an ERROR state function, then when your state blows up, it will
        transition to ERROR state and call your function right away.  It will then
        stay in the ERROR state unless you return a different one.
        """
        if self.RELOAD:
            self.reload()

        called_count = 0

        for func, matchkw in self._collect_matches(message):
            LOG.debug("Matched %r against %s.", message.To, func.__name__)

            if salmon_setting(func, 'locking'):
                with self.call_lock:
                    self.call_safely(func, message, matchkw)
            else:
                self.call_safely(func, message,  matchkw)

            called_count += 1

        if called_count == 0:
            self._enqueue_undeliverable(message)

    def call_safely(self, func, message, kwargs):
        """
        Used by self to call a function and log exceptions rather than
        explode and crash.
        """
        from salmon.server import SMTPError

        try:
            func(message, **kwargs)
            LOG.debug("Message to %s was handled by %s.%s",
                      message.To, func.__module__, func.__name__)
        except SMTPError:
            raise
        except Exception:
            self.set_state(func.__module__, message, 'ERROR')

            if self.UNDELIVERABLE_QUEUE is not None:
                self.UNDELIVERABLE_QUEUE.push(message)

            if self.LOG_EXCEPTIONS:
                LOG.exception("!!! ERROR handling %s.%s", func.__module__, func.__name__)
            else:
                raise

    def clear_states(self):
        """Clears out the states for unit testing."""
        with self.lock:
            self.STATE_STORE.clear()

    def clear_routes(self):
        """Clears out the routes for unit testing and reloading."""
        with self.lock:
            self.REGISTERED.clear()
            del self.ORDER[:]

    def load(self, handlers):
        """
        Loads the listed handlers making them available for processing.
        This is safe to call multiple times and to duplicate handlers
        listed.
        """
        with self.lock:
            for module in handlers:
                try:
                    __import__(module, globals(), locals())

                    if module not in self.HANDLERS:
                        # they didn't specify a key generator, so use the
                        # default one for now
                        self.HANDLERS[module] = DEFAULT_STATE_KEY
                except ImportError:
                    if self.LOG_EXCEPTIONS:
                        LOG.exception("ERROR IMPORTING %r MODULE:" % module)
                    else:
                        raise

    def reload(self):
        """
        Performs a reload of all the handlers and clears out all routes,
        but doesn't touch the internal state.
        """
        with self.lock:
            self.clear_routes()
            for module in list(sys.modules.keys()):
                if module in self.HANDLERS:
                    try:
                        reload(sys.modules[module])
                    except (TypeError, NameError, ImportError):
                        if self.LOG_EXCEPTIONS:
                            LOG.exception("ERROR RELOADING %r MODULE:" % module)
                        else:
                            raise


Router = RoutingBase()


class route:
    """
    The @route decorator is attached to state handlers to configure them in the
    Router so they handle messages for them.  The way this works is, rather than
    just routing working on only messages being sent to a state handler, it also uses
    the state of the sender.  It's like having routing in a web application use
    both the URL and an internal state setting to determine which method to run.

    However, if you'd rather than this state handler process all messages
    matching the @route then tag it @stateless.  This will run the handler
    no matter what and not change the user's state.
    """

    def __init__(self, format, **captures):
        r"""
        Sets up the pattern used for the Router configuration.  The format
        parameter is a simple pattern of words, captures, and anything you
        want to ignore.  The captures parameter is a mapping of the words in
        the format to regex that get put into the format.  When the pattern is
        matched, the captures are handed to your state handler as keyword
        arguments.

        For example, if you have::

            @route("(list_name)-(action)@(host)",
                list_name='[a-z]+',
                action='[a-z]+', host='test\.com')
            def STATE(message, list_name=None, action=None, host=None):
                pass

        Then this will be translated so that list_name is replaced with [a-z]+,
        action with [a-z]+, and host with 'test.com' to produce a regex with the
        right format and named captures to that your state handler is called
        with the proper keyword parameters.

        You should also use the Router.defaults() to set default things like the
        host so that you are not putting it into your code.
        """
        self.captures = Router.DEFAULT_CAPTURES.copy()
        self.captures.update(captures)
        self.format = self.parse_format(format, self.captures)

    def __call__(self, func):
        """Returns either a decorator that does a stateless routing or
        a normal routing."""
        self.setup_accounting(func)

        if salmon_setting(func, 'stateless'):
            @wraps(func)
            def routing_wrapper(message, *args, **kw):
                func(message, *args, **kw)
        else:
            @wraps(func)
            def routing_wrapper(message, *args, **kw):
                next_state = func(message, *args, **kw)

                if next_state:
                    Router.set_state(next_state.__module__, message, next_state.__name__)

        Router.register_route(self.format, routing_wrapper)
        return routing_wrapper

    def __get__(self, obj, of_type=None):
        """
        This is NOT SUPPORTED.  It is here just so that if you try to apply
        this decorator to a class's method it will barf on you.
        """
        raise NotImplementedError("Not supported on methods yet, only module functions.")

    def parse_format(self, format, captures):
        """Does the grunt work of conversion format+captures into the regex."""
        for key in captures:
            format = format.replace("(" + key + ")", "(?P<%s>%s)" % (key, captures[key]))
        return "^" + format + "$"

    def setup_accounting(self, func):
        """Sets up an accounting map attached to the func for routing decorators."""
        salmon_setting(func, 'format', self.format)
        salmon_setting(func, 'captures', self.captures)


def salmon_setting(func, key, value=_DEFAULT_VALUE):
    """Get or set a salmon setting on a handler function"""
    try:
        salmon_settings = getattr(func, SALMON_SETTINGS_VARIABLE_NAME)
    except AttributeError:
        salmon_settings = {}
        setattr(func, SALMON_SETTINGS_VARIABLE_NAME, salmon_settings)
    if value is not _DEFAULT_VALUE:
        salmon_settings[key] = value
    else:
        return salmon_settings.get(key)


def has_salmon_settings(func):
    return hasattr(func, SALMON_SETTINGS_VARIABLE_NAME)


class route_like(route):
    """
    Many times you want your state handler to just accept mail like another
    handler.  Use this, passing in the other function.  It even works across
    modules.
    """
    def __init__(self, func):
        self.format = salmon_setting(func, 'format')
        self.captures = salmon_setting(func, 'captures')
        if self.format is None or self.captures is None:
            raise TypeError("{} is missing a @route".format(func))


def stateless(func):
    """
    This simple decorator is attached to a handler to indicate to the
    Router.deliver() method that it does NOT maintain state or care about it.
    This is how you create a handler that processes all messages matching the
    given format+captures in a @route.

    Another way to think about a @stateless handler is that it is a pass-through
    handler that does its processing and then passes the results on to others.

    Stateless handlers are NOT guaranteed to run before the handler with state.
    """
    salmon_setting(func, 'stateless', True)
    return func


def nolocking(func):
    """
    Does nothing, as no locking is the default now
    """
    warnings.warn("@nolocking is redundant and can be safely removed from your handler %s" % func,
                  category=DeprecationWarning, stacklevel=2)
    return func


def locking(func):
    """
    Salmon assumes your handlers are thread-safe, but is not always the case.
    Put this decorator on any state functions that are not thread-safe for
    whatever reason.
    """
    salmon_setting(func, 'locking', True)
    return func


def state_key_generator(func):
    """
    Used to indicate that a function in your handlers should be used
    to determine what they key is for state storage.  It should be a
    function that takes the module_name and message being worked on
    and returns a string.
    """
    Router.HANDLERS[func.__module__] = func
    return func
