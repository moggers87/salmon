=====================
HTML Email Generation
=====================

HTML Email is apparently the killer feature for everyone who uses email.
The first, second, and third question I get asked when I tell people
about Salmon is, "Does it do HTML email?!"  Yes it does, and hopefully
in a very nice clean way that'll make blasting out all that great
marketing material your users *love* easier than ever.

bq. The fourth question is whether Salmon handles bounces.  :doc:`Yes it does. <bounce_detection>`


A Few Tips About HTML Email
---------------------------

First, you *must* educate your marketing people that your user's `Inbox is not a TV. <http://myinboxisnota.tv/>`_
I actually run `myinboxisnota.tv <http://myinboxisnota.tv/>`_ just to make a point that people who
do marketing have the wrong idea of people's Inbox experience.  It's your job as the hacker to
educate them and make sure that they know users actually mostly hate HTML email, and that sending
them an HTML email is nothing like sending them a commercial on TV.

The next tip is a technical one related to how you have to craft your HTML.  Salmon's
`salmon.html <http://salmonproject.org/docs/api/salmon.html-module.html>`_ API actually
helps you get this right, but you need to understand it in order to appreciate what
it does for you.

The rule when crafting your HTML is that you need to code for browsers of circa 1995
with no ability to use ``style`` tags or ``script`` tags.  Most of the various HTML viewing
clients strip or disable these making them useless.  This means you have to put all
CSS stylings inline into your HTML, and you have to rely on "taboo" tags like ``center``
and ``table`` for your layout.


The Structure Of HtmlMail
-------------------------

The `salmon.html.HtmlMail <http://salmonproject.org/docs/api/salmon.html.HtmlMail-class.html>`_ class
is responsible for generating all your HTML emails.  How it works is you give construct one
with an "outer template" and a `CleverCSS <http://sandbox.pocoo.org/clevercss/>`_ template as your
CSS stylesheet.  This builds a generator that you then hand an internal version of your email
to generate the content for each user.

This combination of outer template+CleverCSS and inner markdown content means that you can
use the markdown content also as your text version, since markdown actually looks half-decent
as a text format.

Here's a simple example that shows this process in action:

<pre class="code prettyprint">
generator = html.HtmlMail("style.css", "html_test.html", {})

resp = generator.respond({}, "content.markdown",
                       From="zedshaw@zedshaw.com",
                       To="zedshaw@zedshaw.com",
                       Subject="Test of an HTML mail.",
                       Body="content.markdown")
</pre>

First, we make a generator passing in the CleverCSS stylesheet ``style.css``,
and the Jinja2 HTML template ``html_test.html``.  Then we call ``HtmlMail.respond``
to craft a `salmon.mail.MailResponse <http://salmonproject.org/docs/api/salmon.mail.MailResponse-class.html>`_
that you can then hand to `salmon.server.Relay <http://salmonproject.org/docs/api/salmon.server.Relay-class.html>`_
for delivery.

There's also a couple of tricks in the above email.  First, notice that the
second parameter is "content.markdown", but that we also pass in the Body="content.markdown".
This little convenience tells the HtmlMail object that you want to reuse the
raw ``content.markdown`` file as the text/plain version of the email.

Finally, once you make the generator you can keep calling ``respond`` to spit out
each message you want.

The HTML CSS Conversion
-----------------------

None of the above code shows you what is the nicest part of this API.  The salmon.html
API will actually take plain HTML and your CleverCSS and insert the ``style`` attributes
into it for you.  Let's look at an example from the unit test (that's disgusting).
First we have the CleverCSS template:

<pre class="code prettyprint">
body:
    margin: 10
    padding: 20
    background: green - 30
    color: blue

    h1:
        font-size: 3em
    h2:
        font-size: 2em
        color: yellow

    h3:
        font-size: 1em

    p:
        padding: 0.3em
        background: red

h2:
    color: yellow

#bright:
    background: black
    color: white

.dull:
    background: gray
    color: black
</pre>

Then we have the raw original HTML:

<pre class="code prettyprint">
&lt;html&gt;
    &lt;head&gt;
        &lt;title&gt;{{ title }}&lt;/title&gt;
    &lt;/head&gt;

    &lt;body style="background: magenta"&gt;
        &lt;h1 class="bright"&gt;{{ title }}&lt;/h1&gt;

        {{ content }}

        &lt;h3 id="dull"&gt;All done.&lt;/h3&gt;
    &lt;/body&gt;
&lt;/html&gt;
</pre>

Notice this is a template too, and that {{ content }} is your ``content.markdown`` file
from the earlier discussion.

Now when you run this (including the content.markdown not shown here), Salmon produces
this:

<pre class="code prettyprint">
&lt;html&gt;
&lt;head&gt;
&lt;title&gt;&lt;/title&gt;
&lt;/head&gt;
&lt;body style="background: magenta; margin: 10; padding: 20; background: #006200; color: blue"&gt;
&lt;h1 class="bright" style="font-size: 3em; background: black; color: white"&gt;&lt;/h1&gt;
&lt;h1 style="font-size: 3em"&gt;Hello&lt;/h1&gt;
&lt;p style="padding: 0.3em; background: red"&gt;I would &lt;em&gt;love&lt;/em&gt; for you to tell me what is going on here joe.  NOW!&lt;/p&gt;
&lt;h2 style="font-size: 2em; color: yellow; color: yellow"&gt;Alright&lt;/h2&gt;
&lt;p style="padding: 0.3em; background: red"&gt;This is the best I can come up with.&lt;/p&gt;
&lt;p style="padding: 0.3em; background: red"&gt;Zed&lt;/p&gt;
&lt;h3 id="dull" style="font-size: 1em; background: gray; color: black"&gt;All done.&lt;/h3&gt;
&lt;/body&gt;
&lt;/html&gt;
</pre>

Which, if you code for a Web 2.0 company is probably making your eyes bleed Dijon mustard, but it
works.  Salmon has walked your HTML and inserted all the style tags it could, including
keeping any you already had there.

Conclusion
----------

With Salmon HTML email API you should be able to blast out all the wonderful HTML you need
to prop up your sales needs for years to come.  It does the best it can to make it easy
to still work in a modern web methodology, but produce the nasty HTML that has the highest
chance of working in most email clients.


