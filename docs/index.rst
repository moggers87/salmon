.. Salmon documentation master file, created by
   sphinx-quickstart on Sun May 17 14:03:32 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root ``toctree`` directive.

====================
Salmon Documentation
====================

This is the Salmon documentation, organized into categories from "newbie" to
"expert".

Initial Concepts
----------------

* :doc:`faq` -- Questions people have asked about Salmon.
* :doc:`getting_started` -- A fast tour of getting Salmon going and doing
  something with it.
* :doc:`salmon_commands` -- All of the commands Salmon supports.  You can get
  at this with ``salmon-help``.
* :doc:`introduction_to_finite_state_machines` -- Important to understand the
  simplified version of Finite State Machines Salmon uses.

Advanced Concepts
-----------------

* :doc:`deferred_processing_to_queues` -- Very handy way of processing mail.
* :doc:`writing_a_state_storage` -- You'll need this if you want to store state
  in the database.
* :doc:`primary_vs_secondary_registration` -- The concept of doing registration
  in Salmon, where contacting the service the first time is the registration.
* :doc:`hooking_into_django` -- Shows you how to get access to a Django ORM
  model.

Deployment
----------

* :doc:`salmon_virtual_env` -- Quick instructions for setting up your Salmon in
  a virtualenv for your first simple  deployment.
* :doc:`deploying_salmon` -- This is for when you're getting more serious about
  deployment.  Involves building a completely separate virtualenv+python for
  Salmon and shows deploying oneshotblog in it.
* :doc:`deploying_salmon_level_2` -- At this level of deployment you are
  running multiple sites on the same server using a virtualhost setup, and you
  have each application installed under its own user.

Deployment: Examples
--------------------

* :doc:`deploying_oneshotblog`

Specific Features
-----------------

* :doc:`unit_testing` -- Salmon has a few simple things to help write better
  mail specific unit tests.
* :doc:`confirmations` -- Confirming a user so that you validate they are an
  actual email address.
* :doc:`filtering_spam` -- How to use Salmon's spam blocking features.  It's
  easy to use, but a bit hairy to setup.
* :doc:`bounce_detection` -- Using Salmon's bounce message parser to handle
  bounces.
* :doc:`unicode_encoding_and_decoding` -- How Salmon decodes the nastiest email
  into Unicode, and then converts Unicode back into a clean email for sending.
* :doc:`html_email_generation` -- Using Salmon's HTML email generation library
  to send out HTML to annoy everyone with.

Source documentation
--------------------

.. currentmodule:: salmon

.. autosummary::
   :toctree: generated/

   salmon.handlers
   salmon.bounce
   salmon.commands
   salmon.confirm
   salmon.encoding
   salmon.mail
   salmon.queue
   salmon.routing
   salmon.server
   salmon.testing
   salmon.utils
   salmon.version
   salmon.view

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

