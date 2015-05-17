==================================
Primary vs. Secondary Registration
==================================

When you design a Salmon application the question of "registration" comes up
almost immediately.  The question is one of how you find out who a person is so
that you can interact with them.  In the web world this involves a form of some
kind asking for a login and password at a minimum.  Some sites even go so far
as to require a sign-up process *before* they let you see anything about the
site, or even their marketing material.

On the web this kind of registration is what I like to call "Primary
Registration".  It comes from the concept of primary vs. secondary data, or
primary vs. secondary analysis.  In the world of measurement a primary source
is one that you gathered the information from directly, usually by giving them
a questionaire.  A secondary source is one that you gathered in some indirect
way, either by evaluating past research in a new way, data mining, or simply
unobtrusive data collection.

With a web site you *must* have a primary registration system.  There is no
implied identity in a browser that is consistent for a user, so you need to ask
them for some information and associate their stateless browser to a cookie or
similar tracking mechanism.  You have to do this for each session you start
with them, and to register them if your service requires some kind of password
protection.

In the world of the web primary registration is just how things are done.

Secondary Registration
----------------------

Salmon give you the ability to do *Secondary Registration* where the act of
interacting with your service *is* the registration.  A typical primary
registrationg process will ask for a user's email address to identify the user,
but in Salmon the user actively gives your service their email address to start
playing.  Their first message to your service actually has all the information
you need to sign them up and give them their first taste of your service.

In fact, a user's identity is so baked into the email protocols that your
Salmon server has almost the inverse problem:  it's too easy to fake an
identity, so you need to confirm their subscription and important actions.
This confirmation is traditionally nothing more than a reply asking them to
reply with some random number in the address.  If you get a reply to this
auto-generated email address then you assume they are real.

bq. This "random number confirmation handshake" is important because SMTP
allows anyone with an internet connection to lie about who they are and craft a
fake email claiming to be someone else.  The confirmation assures you that the
supposed sender has at least received an email in their inbox and that it had
the random number you generated in the reply address.  A determined hacker
could also get past that, but if you have that situation you are dealing with
more problems than just confirmations.

Once you do though you are fairly assured that they are identified *and* using
your service.  It ends up being the most low effort entry to your service you
could possibly devise without making the service unsafe.


Comparing Two Designs
---------------------

When you sit down to build a Salmon application you may still think about
registration in the primary way, but a secondary registration is typically more
natural for an email service.  To illustrate the point, let's say you are
creating an online game using Salmon, and you want people to register for the
game.

With a primary registration you would approach the problem by making your game
open only to registered users.  If they send an email to your game you send a
single reply pointing them at the web page they can use to sign up.  You also
then take every email and pass it through a filter that checks that the user is
registered in your subscription database.  This is mostly how you would do it
in a web application.

bq. Maybe there is a legitimate reason to force a user to a web page to give a
password and other information before using the service.  If that's the case,
then go for it, but consider trying to make the *entry* to your service a
secondary registration that then asks them to do a full registration to get
more features.

With a secondary registration system, you are using Salmon's ability to track
the state of every user to know whether they are registered or not.  When your
game receives their first email, it would transition to an ``UNKNOWN`` state and
reply with a confirmation email.  Once they reply to the confirm email you
transition from ``UNKNOWN`` to the rest of the game since they are now
registered.  Every interaction after that will simply know they are registered
because they are in the right state.

This has a big impact on your game's design because now you do *not* need to
check the database on every received email to confirm their identity.  Their
email address and their state in your state's storage tells you that
implicitly.

You can also extend this to other requirements for your system.  You can use
their known state to transition them from free to paid quality services, to
suspended states, to pause them after a bounce, and back to normal activity.


Invite Only Systems
-------------------

An invite only system can also use the secondary registration technique by
having the inviter's invitation request create a record for the invitee that's
in the right start state.  When the inviter tells you to invite their friend,
you create a state for the friend that says ``INVITED`` and use the invite as a
sort of implied confirmation email.  When the invitee replies to this invite
email, you transition them to the rest of the system as they've now registered.

Another way to think of an invite only system in Salmon is as a 3rd-party
confirmation.  Rather than the target user (the invitee) prompting a
confirmation, it is their friend sending the invite (the inviter) who triggers
the confirmation process on behalf of their buddy.

An additional bonus with Salmon is that the state of the invitee is known, so
if the inviter tries to send them again, or if someone else does, then you know
they already were sent an invite.  You can just ignore the request and
avoid spamming people.  You can also run reports to find out your
conversion rates by simply looking for everyone in the various states and
counting.


Security And Design Issues
--------------------------

Doing these kind of secondary registrations and implied identity does come with
an extra security penalty.  Unless your system is incorporating S-MIME or GPG
you won't have a solid way to identify the sender.  You don't have this on most
other internet services either so it's not much of a loss.  At least with email
you have a higher assurance that this is a real person.

When you design your service it's a good idea to:

# Either make everything the user does non-destructive,
# Send confirmations for anything desctructive,
# Or bounce them to a web site for more complex interactions and security.

You should also make any confirmations you send easily replied to, but have a
good random number in them that you remember for later.  In fact, if you use
the "salmon.confirm" API you get all of this for free and done the right way.




