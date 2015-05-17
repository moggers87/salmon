========================================
 Writing A Salmon State Storage Backend
========================================

Earlier versions of Salmon assumed that you would use SQLAlchemy, and that you
wouldn't mind storing your state in the database using SQLAlchemy.  Well,
during the 0.9 redesign it became very easy to let you store the state however
and wherever you want.  In the new Salmon setup there is a bit more work to
create alternative storage, but Salmon comes with two default stores that you
can use to get started.

The Default MemoryStore
-----------------------

When you get started with Salmon you'll definitely not want to go through the
trouble of setting up a custom store.  For your first days of development,
using the default
`MemoryStorage <http://salmonproject.org/docs/api/salmon.routing.MemoryStorage-class.html>`_
is the way to go.  After you get further in your development you want to switch
to the
`ShelveStorage <http://salmonproject.org/docs/api/salmon.routing.ShelveStorage-class.html>`_
to store the state in a simple Python
`shelve <http://docs.python.org/library/shelve.html>`_ store.


``MemoryStorage`` keeps the routing state in a simple dict in memory, and doesn't
provide any thread protection.  Its purpose is for developer testing and unit
test runs where keeping the state between disks is more of a pain than it is
worth.  Use the ``MemoryStorage`` (which is the default) for your development
runs and for simple servers where the state does need to be maintained (very
rare).


Here's the code to MemoryStore for you to just look at, it's already included in Salmon:

<pre class="code prettyprint">
class MemoryStorage(StateStorage):
    """
    The default simplified storage for the Router to hold the states.  This
    should only be used in testing, as you'll lose all your contacts and their
    states if your server shutsdown.  It is also horribly NOT thread safe.
    """
    def __init__(self):
        self.states = {}

    def get(self, module, sender):
        key = self.key(module, sender)
        try:
            return self.states[key]
        except KeyError:
            self.set(module, sender, ROUTE_FIRST_STATE)
            return ROUTE_FIRST_STATE

    def set(self, module, sender, state):
        key = self.key(module, sender)
        self.states[key] = state

    def key(self, module, sender):
        return repr([module, sender])

    def clear(self):
        self.states.clear()
</pre>

As you can see there isn't much to implement to make your own storage
for Salmon to use.

bq.  Keep in mind that this is just the storage *Salmon* needs to operate,
you probably don't want to be accessing this in your own application,
and instead probably want to access the store you create yourself.


The ShelveStorage
-----------------

``ShelveStorage`` is used for your small deployments where you are mostly just
testing the deployment process or doing a small service.  It will store your
data between runs, and is probably fast enough for most sites, but you'll want
to ditch it if you ever:

# Run more than one process that needs the state information.
# Start to store everything in a database anyway.

The code to ShelveStorage (which is *already* part of Salmon) is more complex
since it must keep the threads happy, but you should read through it to get
an idea of how a more complex state store would work:


<pre class="code prettyprint">
class ShelveStorage(MemoryStorage):
    """
    Uses Python's shelve to store the state of the Routers to disk rather than
    in memory like with MemoryStorage.  This will get you going on a small
    install if you need to persist your states (most likely), but if you
    have a database, you'll need to write your own StateStorage that
    uses your ORM or database to store.  Consider this an example.
    """
    def __init__(self, database_path):
        """Database path depends on the backing library use by Python's shelve."""
        self.database_path = database_path
        self.lock = threading.RLock()

    def get(self, module, sender):
        """
        This will lock the internal thread lock, and then retrieve from the
        shelf whatever module you request.  If the module is not found then it
        will set (atomically) to ROUTE_FIRST_STATE.
        """
        with self.lock:
            store = shelve.open(self.database_path)
            try:
                key = store[self.key(module, sender)]
            except KeyError:
                self.set(module, sender, ROUTE_FIRST_STATE)
                key = ROUTE_FIRST_STATE
            return key

    def set(self, module, sender, state):
        """
        Acquires the self.lock and then sets the requested state in the shelf.
        """
        with self.lock:
            store = shelve.open(self.database_path)
            store[self.key(module, sender)] = state
            store.close()

    def clear(self):
        """
        Primarily used in the debugging/unit testing process to make sure the
        states are clear.  In production this could be a bad thing.
        """
        with self.lock:
            store = shelve.open(self.database_path)
            store.clear()
            store.close()
</pre>



Using The ShelveStorage
-----------------------

You can use ``ShelveStorage`` by simply adding this line to your ``config/boot.py``
file just before you do anything else with the ``Router``:

<pre class="code prettyprint">
from salmon.routing import ShelveStorage
Router.STATE_STORE=ShelveStorage("run/states")
</pre>

It actually doesn't matter currently when you do it, but it's good practice right now.

After you do that, restart salmon and it will start using the new store.
Notice that your *tests will not use this*.  It's not a good idea to have tests
use ``ShelveStorage``, but if you want to turn it on for a run to see what
happens, then you can modify ``config/testing.py`` the same way.  You could also
write a unit test that did this temporarily by putting that line in your test
case.


What To Implement
-----------------

If you want to implement your own then you just have to implement the methods
in
`StateStorage <http://salmonproject.org/docs/api/salmon.routing.StateStorage-class.html>`_
and make sure it behaves the same as MemoryStorage.  Look at the code to
ShelveStorage for a moment to see what you need:

<pre class="code prettyprint">
class StateStorage(object):
    """
    The base storage class you need to implement for a custom storage
    system.
    """
    def get(self, module, sender):
        """
        You must implement this so that it returns a single string
        of either the state for this combination of arguments, OR
        the ROUTE_FIRST_STATE setting.
        """
        raise NotImplementedError("You have to implement a StateStorage.get.")

    def set(self, module, sender, state):
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
</pre>

There really isn't much to it, just methods to get and set based on the module
and sender's email address.  Also notice that you don't have to make it
readable in any complete sense, since Salmon doesn't do anything other than
get, set, and clear the state store (and it only clears on reloads and in
testing).


Important Considerations
------------------------

I am purposefully *not* telling you how to exactly implement it because I'm not
exactly sure what is needed as of the 0.9 release.  I use the the
ShelveStorage, but I'd like to hear what other people have written and then
start building infrastructure to make that easier.

There are some important things to consider when you implement your storage
though:

# Make sure that the calls to all methods are thread safe, and potentially process safe.
# If you do thread locking, use the *with* statement and an RLock.
# If your storage is potentially very slow, then consider a caching scheme inside, but *write that after making it work correctly.*
# Do *NOT* be tempted to store junk in this like it is a "session".  It should be lean and mean and only do state.
# Make sure you keep the key being used exactly as given.  You can seriously mess up Salmon's Router if you start getting fancy.

Attaching It To The Router
--------------------------

Your storage backend will then be attached to the salmon.routing.Router in the
same way as what you did with ShelveStorage.  It really should be that simple
since the data stored in the state store is very minimal.


Other Examples
--------------

If you want more examples then you can look at the ``examples/librelist`` code to see
how `librelist.com <http://librelist.com/>`_ uses `Django <http://www.djangoproject.com/>`_
to store the state.
