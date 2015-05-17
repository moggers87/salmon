==========================================
Installing Salmon Into Virtualenv With Pip
==========================================


The best way to install Salmon in a virtualenv is using the "pip
tool":http://pip.openplans.org/ to install it. This will automatically fetch
the code from bazaar, install it inside the virtualenv and fetch any missing
dependencies.

First, if you haven't already, you'll need to install pip. Make sure
you've activated the virtualenv:

<pre class="code">
. bin/activate
</pre>

from the root of the virtualenv, and then run:

<pre class="code">
easy_install -U pip
</pre>

Then just do:

<pre class="code">
pip install salmon
</pre>

Credits
-------

These instructions were donated to Salmon by "Zachary
Voase":http://disturbyte.github.com but `contact me </contact.html>`_ for
suggested improvements.
