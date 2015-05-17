=============================
Unicode Encoding And Decoding
=============================


The world is Unicode, but email existed long before that world.  Salmon uses
special encoding/decoding gear that takes just about any nasty horrible pre-Unicode
email it gets and converts it to a perfect little Unicode fantasy.  You do all
your work in the Unicode world, which Python favors, and then when you're ready
to send, Salmon intelligently figures out how to make an email that anyone can
read.

The added advantage of doing this conversion is that Salmon by default also
cleans up all the various tricks spammers use to get around spam checkers.  Because
it's doing a conversion from just first principles of "everything must become Unicode"
the end result is a crystal clear piece of data you can filter.  When you then
output the same message, it gets reconverted to sane easily parseable message.

Salmon is also so persistent in this conversion that it can convert nearly every
message that's valid, and the very tiny percentage it can't (less 1/1000th of a percent)
are entirely screwed up spam that should not be transmitted anyway.

bq. This gear apparently doesn't support pre-Hindic sanskrit, but then again neither
does Python.

Why
---

Sometimes people ask why Salmon would bother converting everything to Unicode?
The reason is simple:  everything you deal with now is Unicode.  Either it's in
a representation like UTF-8, or it's internally a Python Unicode string.  Databases,
web frameworks, ORM, network protocols, and the entire internet is Unicode.

However, there's another practical reason.  If you were to start using Salmon to
process email, you would end up inventing almost the exact same gear to convert
headers and bodies to Unicode.  The only difference is you would do it in a typical
hacker half-assed fashion that only solved your immediate problems, and you wouldn't
do it in a global useful way.

The Salmon encoding gear is basically what you should be making to deal with email
in a modern language.

How
---

The `salmon.encoding <http://salmonproject.org/docs/api/salmon.encoding-module.html>`_ module
is the main meat of this conversion magic.  This code is probably the most dense
part of Salmon since it has to use various parsing tricks and heuristics to figure
out how to get every part of the message into a Unicode string.

The primary trick used is that Salmon does not trust anything it's given, and when
python fails to convert a header or body, it uses the wonderful `chardet <http://chardet.feedparser.org/>`_
library to guess at what the encoding should be based on the contents.  If this fails
then the entire data is considered suspect and the message is rejected.

This turns out to be surprisingly accurate in practice, and it even corrects some
invalid clients that fail to encode Subject lines but still place Chinese encodings
in them.  Salmon will take those unencoded headers, fail to convert them to ascii,
run chardet on them to see they are actually Chinese, and then convert them accurately.

The Rules
---------

A set of axioms controls how the encoding is done:

# NO ENCODING IS TRUSTED, NO LANGUAGE IS SACRED, ALL ARE SUSPECT.
# Python wants Unicode, it will get Unicode.
# Any email that CANNOT become Unicode, CANNOT be processed by Salmon or Python.
# Email addresses are ESSENTIAL to Salmon's routing and security, and therefore will be canonicalized and properly encoded.
# Salmon will therefore try to "upgrade" all email it receives to Unicode internally, and cleaning all email addresses.
# It does this by decoding all codecs, and if the codec LIES, then it will attempt to statistically detect the codec using chardet.
# If it can't detect the codec, and the codec lies, then the email is bad.
# All text bodies and attachments are then converted to Python Unicode in the same way as the headers.
# All other attachments are converted to raw strings as-is.

Once Salmon has done this, your Python handler can now assume that all
MailRequest objects are happily Unicode enabled and ready to go.  The rule is:

    IF IT CANNOT BE UNICODE, THEN PYTHON CANNOT WORK WITH IT.

On the outgoing end (when you send a MailResponse), Salmon tries to create the
email it wants to receive by canonicalizing it:

# All email will be encoded in the simplest cleanest way possible without losing information.
# All headers are converted to 'ascii', and if that doesn't work, then 'utf-8'.
# All text/* attachments and bodies are converted to ascii, and if that doesn't work, 'utf-8'.
# All other attachments are left alone.
# All email addresses are normalized and encoded if they have not been already.


Neat Tricks
-----------

The end result of this is that you can now take any email and then convert it to
any modern data format and send it over new protocols.  For example, here's the
code from `librelist.com <http://librelist.com/>`_ to implement the JSON dump
for the `archive browser <http://librelist.com/browser/>`_ Javascript interface:

<pre class="code prettyprint">
def json_encoding(base):
    ctype, ctp = base.content_encoding['Content-Type']
    cdisp, cdp = base.content_encoding['Content-Disposition']
    ctype = ctype or "text/plain"
    filename = ctp.get('name',None) or cdp.get('filename', None)

    if ctype.startswith('text') or ctype.startswith('message'):
        encoding = None
    else:
        encoding = "base64"

    return {'filename': filename, 'type': ctype, 'disposition': cdisp,
            'format': encoding}

def json_build(base):
    data = {'headers': base.headers,
                'body': base.body,
                'encoding': json_encoding(base),
                'parts': [json_build(p) for p in base.parts],
            }

    if data['encoding']['format'] and base.body:
        data['body'] = base64.b64encode(base.body)

    return data

def to_json(base):
    return json.dumps(json_build(base), sort_keys=True, indent=4)
</pre>

Since this code can assume that everything inside Salmon is fully Unicode, it only needs
to worry about binary items like images and encode those as base64.

salmon cleanse
--------------

You can also use the ``salmon cleanse`` command to take a Maildir or mbox as input, and
then convert it into a cleaned up Maildir as output.  Try it on some of your spam
folders to watch the magic.

Reporting Problems
------------------

If you happen to run into a message that you feel Salmon should accurately
decode, feel free to `report it </contact.html>`_ and I'll take a look.


