==========================
Hooking Salmon Into Django
==========================


This is a short document because using `Django <http://www.djangoproject.com/>`_ ORM is very simple from Salmon.  The trick is
to fake out Django so that when you import the Django model into Salmon, the Django model
knows where it's living and will operate.  We'll go through an "integration" step
by step.


Step 1:  Make Your Django App Work
----------------------------------

There's no point in trying to import an ORM that doesn't work.  So get it working,
maybe write some tests.

An important thing is that you should be able to run ``python manage.py shell`` and import
your model without problems.


Step 2: Fake Out Django
-----------------------

You then have to put an environment variable in your Salmon ``config/settings.py`` file before
you load any Django Models:

<pre class="code prettyprint">
os.environ['DJANGO_SETTINGS_MODULE'] = 'webapp.settings'
</pre>

This is from the `librelist.com <http://librelist.com/>`_ examples, where the Django
models are in ``webapp`` so we our settings module from Salmon perspective is ``webapp.settings``.


Step 3:  Use The Django Models
------------------------------

After that, you can just import your models however you want.  Here's an example of
Librelist using a Django Model to store confirmations:

<pre class="code prettyprint">
from webapp.librelist.models import Confirmation

class DjangoConfirmStorage():
    def clear(self):
        Confirmation.objects.all().delete()

    def get(self, target, from_address):
        confirmations = Confirmation.objects.filter(from_address=from_address,
                                                list_name=target)
        if confirmations:
            return confirmations[0].expected_secret, confirmations[0].pending_message_id
        else:
            return None, None

    def delete(self, target, from_address):
        Confirmation.objects.filter(from_address=from_address,
                                                list_name=target).delete()

    def store(self, target, from_address, expected_secret, pending_message_id):
        conf = Confirmation(from_address=from_address,
                            expected_secret = expected_secret,
                            pending_message_id = pending_message_id,
                            list_name=target)
        conf.save()
</pre>


Well, That Wasn't Too Hard
--------------------------

The only thing you'll have to contend with is where code you need to use these models
lives.  Since it's all Python, you can just import what you need, but my recommendation
is to focus most of your model code into your Django application, and then only put
a small amount into Salmon.

For more information, look in the `Salmon source releases </releases/>`_ to see how
Django is used in the ``examples/librelist`` code.

