==================================================
 A Painless Introduction To Finite State Machines
==================================================

Salmon uses the concept of a Finite State Machine to do the internal processing
and keep track of what it should do next.  You don't necessarily need to know
the details of how a FSM works, but it helps you if you want to know enough
about Salmon to do advanced work.  Most people could be blissfully unaware of
state machines and still do plenty of work with Salmon.

Your Computer Science Class Sucked
----------------------------------

When I say "finite state machine" everyone reads it as:

bq. "FINITE STATE MACHINE!!!!! OMGWTFBBQ THOSE ARE HARD!!!!"

Yes, the way your professor explained FSM makes them much harder than they are
in practice.  You were probably thrown fairly random sounding terms like
"edge", "node", "transitions", "acceptors", "recognizers", and "transducers".
You were probably shown graphs with lines and circles and told confusingly that
the lines were edges and the circles were nodes, but that the edges were states
unless you used this kind where the edges were transitions and that kind where
the circles were states.

Alright, just forget about that because they aren't really that complicated.  A
practical finite state machine is basically four things:

* A bunch of functions, or things that need to get done.
* A bunch of events, or reasons to call these functions.
* Some piece of data that tracks the "state" this bunch of functions is in.
* Code inside the functions that says how to "transition" or "change" into the next state for further processing.

That is really all there is to every FSM.  Sure you can change around what a
state is, add code that runs on a transition, or make FSM that "inherit" from
other FSM, but in the end they are all:

bq. functions, events, states, transitions

That is all there is to it, no matter how you slice these or dice these up.


Implementing A Practical FSM
----------------------------

Now that we've brought the fear level down, let's actually make one.  This will
be a little toy FSM, but it will get you started and it won't be too far off
from what Salmon uses.

We are going to implement your classic email confirmation system.  This system
usually works like this:

# You receive an email at some service, let's say users-subscribe@test.com.
# You reply to the sender with a confirmation message.
# They reply with an email to your confirmation's random address.
# You receive this, approve the handshake, and make them subscribed with a welcome email.
# They send an email, and since they are subscribed, you post it to the list.

This is a typical operation on most mailing lists, but with a state machine it
turns out to be fairly trivial to implement.

First, we need to look at the above conversation and think about what is more
clear:  states the user will be in, or events that they will generate.  In this
case I'd go with the states they will be in during the conversation:

* START -- Every machine has one of these.
* PENDING -- We sent the confirm, and waiting for their reply.
* POSTING -- They replied to the confirm and can now post.

Notice I gave each state a verb.  You are saying what state this user is in.
"They are currently posting."  You don't say what they "did".  Now, sometimes
it just makes sense to do it differently, so don't be a slave to this setup.
I've just found it helps keep things consistent if you name the states after
what they are currently doing.

Now that we know what kind of states we're dealing with we need to solve the
next two parts of the puzzle:  events or transitions.  In an email application
I like to start with the events, as these are the email addresses and messages
they will be sending me.  What we do now is for each state, list the addresses
we'll consider an "event" for that state.

* START -- (list_name)-subscribe@test.com
* PENDING -- (list_name)-confirm-(id)@test.com
* POSTING -- (list_name)@test.com

This is all the "events" we need right now, written out as email addresses.

bq. If we were to add the ability to unsubscribe, then we would add an event
for (list_name)-unsubscribe@test.com to POSTING so that we could transition
    them from POSTING to say, SLEEPING.

We now have our states, and the events that each state answers.  Last step is
to figure out what state "transitions" to which other state.

Write The Functions
-------------------

At this point, our FSM is simple enough that we could just write the functions,
and the logic of each function would dictate the transitions.  However, if you
had a larger number of states and events you would want to sit down and draw a
diagram or a make a table of the transitions before you wrote some code.

To start our functions we'll just name them after the states and put the events
they handle at the top as pseudo code ``event`` decorators:

<pre class="code prettyprint">
@event("(list_name)-subscribe@test.com")
def START(...):
    """Initial setup of the user."""
    ...

@event("(list_name)-confirm-(id)@test.com")
def PENDING(...):
    """Waiting for them to confirm."""
    ...

@event("(list_name)@test.com")
def POSTING(...):
    """They are posting, anything they send we post."""
    ...
</pre>

This is abbreviating the syntax quite a bit, is not functioning Python code but
it is pretty close.  Instead of ``event`` you would have a ``route`` decorator and
it would have a few regexes.  Otherwise it's about the same.

bq. We could also say that each state handles multiple events, which is what
you would do if POSTING handled the "unsubscribe" requests.

Add Logic And Transitions
-------------------------

The final piece, and the part you'll spend the longest getting right, is
filling in the logic and making the transitions happen.  How would you indicate
*where* each state should go next?  Remember that each state is a simple Python
function, and that to "transition" means to change to another state.  Well, we
have to tell whatever is running the state machine to run a *different*
function next time.

Easiest way to do that is for our handlers to just return the next function.
The "runner" will then take that, store it somewhere, and the next time an
event comes the runner will load the next function to run.

Here's the psuedo code to do just that:

<pre class="code prettyprint">
@event("(list_name)-subscribe@test.com")
def START(...):
    """Initial setup of the user."""
    send_confirmation()
    return PENDING

@event("(list_name)-confirm-(id)@test.com")
def PENDING(...):
    """Waiting for them to confirm."""
    if check_confirmation_is_good():
        send_welcome()
        return POSTING
    else:
        ignore_them()

@event("(list_name)@test.com")
def POSTING(...):
    """They are posting, anything they send we post."""
    deliver_message_to_all()
    return POSTING
</pre>


Right away you can see that we change to the next state by just returning the
actual function to call next.  When the next event comes in, the runner matches
it to the right function, calls it, and then sets up for the next one.

If you look at PENDING, you can see that it either returns POSTING if they
confirm correctly or it just ignores them.  You could also transition to
"return ERROR" if you wanted to put them in an error state and send a different
message.

Looking at POSTING, you see that it just keeps returning itself to indicate
that it is staying there.  If you had POSTING process "unsubscribes" then it
would simply do the unsubscribe confirm, and then transition to UNSUBSCRIBING.
That state function would then check the confirmation and unsubscribe them,
transitioning to something like DEAD or SLEEPING.

bq. An "optimization" in Salmon is that if a state function doesn't return
anything then it's assumed to just want to stay in that state.  In this case
POSTING could have no return and it would work the same.

Jump To vs. Transition
----------------------

You now know pretty much everything you need to handle FSM except for a tiny
corner case.  It is typically called the "epsilon transition" which basically
means "transition to that state without an explicit event".  When you use this
is when your event needs to fire off the code for the *next* transition right
now, rather than waiting for the next event from the user.

In the above pseudo code this is simply done by actually calling that
transition function and returning whatever it returns.  Let's say we wanted to
have PENDING also call POSTING with the original message they sent:

<pre class="code prettyprint">
def PENDING(message):
    if check_confirmation_is_good():
        send_welcome()
        return POSTING (message):
    else:
        ignore_them()

def POSTING(message):
    deliver_message_to_all()
    return POSTING
</pre>

Notice that we changed the ``return POSTING`` to a @return POSTING(...)@ which
returns the results of calling POSTING.

That's it, you now know epsilon transitions.  Man, that was tough.

bq.  The danger of this is if you don't have your FSM carefully mapped out,
then you could call a state that loops back to your state and you're in an
endless loop.  Watch for that.

Why Finite State Machines Anyway
--------------------------------

Finite State Machines like this are very powerful because they behave in ways
that are consistent, easily debugged, and intelligent.  Because the decision of
how each step in the chain of events is controlled by a constrained set of
states, events, and transitions, you can actually avoid many bugs you'd get in
regular classes and objects.

For example, if you were to receive another subscribe message while there is a
confirmation pending, then that event (email address) isn't recognize and just
ignored.  You would see it in the logs, and see that your FSM stayed in the
PENDING state.  If you then wanted PENDING to handle additional requests it's a
simple matter of adding that event and writing the code.

The way to think of the a FSM is it is like an object that has a white list of
functions, parameters, AND allowed values for its private data.  If an FSM
tries to change to a state that doesn't exist it's an error.  If it gets an
event it doesn't know it ignores it.  If you try to transition wrong you see it
in the logs, or it's an error.

FSM also have the debugging advantage of showing you the history of not only
what states were called, but *why* they were called and what they did next.
You will see the entire conversation and can pinpoint exactly where it went
wrong.

However, the most important reason to use FSM is because this is how email and
asynchronous conversations work.  When you have a conversation with someone
there is state involved.  You don't have to start the entire conversation from
scratch at the start of each sentence.  Instead you remember what the person
said and what state you are in (angry, sad, happy) and that controls what you
do next (punch them, run away, hug them) based on the events they send ("screw
you", "you're dead", "i love you").

The use of an FSM will make your Salmon applications seem like magic.  They
will behave more like smart systems that just seems to know like a wizard what
should happen next, and *why* it should happen that way.


