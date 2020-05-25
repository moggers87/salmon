"""
Bounce analysis module for Salmon.  It uses an algorithm that tries
to simply collect the headers that are most likely found in a bounce
message, and then determine a probability based on what it finds.
"""
from functools import wraps
import re

BOUNCE_MATCHERS = {
    'Action': re.compile(r'(failed|delayed|delivered|relayed|expanded)', re.IGNORECASE | re.DOTALL),
    'Content-Description': re.compile(r'(Notification|Undelivered Message|Delivery Report)', re.IGNORECASE | re.DOTALL),
    'Diagnostic-Code': re.compile(r'(.+);\s*([0-9\-\.]+)?\s*(.*)', re.IGNORECASE | re.DOTALL),
    'Final-Recipient': re.compile(r'(.+);\s*(.*)', re.IGNORECASE | re.DOTALL),
    'Received': re.compile(r'(.+)', re.IGNORECASE | re.DOTALL),
    'Remote-Mta': re.compile(r'(.+);\s*(.*)', re.IGNORECASE | re.DOTALL),
    'Reporting-Mta': re.compile(r'(.+);\s*(.*)', re.IGNORECASE | re.DOTALL),
    'Status': re.compile(r'([0-9]+)\.([0-9]+)\.([0-9]+)', re.IGNORECASE | re.DOTALL)
}

BOUNCE_MAX = len(BOUNCE_MATCHERS) * 2.0

PRIMARY_STATUS_CODES = {
    '1': 'Unknown Status Code 1',
    '2': 'Success',
    '3': 'Temporary Failure',
    '4': 'Persistent Transient Failure',
    '5': 'Permanent Failure'
}

SECONDARY_STATUS_CODES = {
    '0':   'Other or Undefined Status',
    '1':   'Addressing Status',
    '2':   'Mailbox Status',
    '3':   'Mail System Status',
    '4':   'Network and Routing Status',
    '5':   'Mail Delivery Protocol Status',
    '6':   'Message Content or Media Status',
    '7':   'Security or Policy Status',
}

COMBINED_STATUS_CODES = {
    '00': 'Not Applicable',
    '10': 'Other address status',
    '11': 'Bad destination mailbox address',
    '12': 'Bad destination system address',
    '13': 'Bad destination mailbox address syntax',
    '14': 'Destination mailbox address ambiguous',
    '15': 'Destination mailbox address valid',
    '16': 'Mailbox has moved',
    '17': 'Bad sender\'s mailbox address syntax',
    '18': 'Bad sender\'s system address',

    '20': 'Other or undefined mailbox status',
    '21': 'Mailbox disabled, not accepting messages',
    '22': 'Mailbox full',
    '23': 'Message length exceeds administrative limit.',
    '24': 'Mailing list expansion problem',

    '30': 'Other or undefined mail system status',
    '31': 'Mail system full',
    '32': 'System not accepting network messages',
    '33': 'System not capable of selected features',
    '34': 'Message too big for system',

    '40': 'Other or undefined network or routing status',
    '41': 'No answer from host',
    '42': 'Bad connection',
    '43': 'Routing server failure',
    '44': 'Unable to route',
    '45': 'Network congestion',
    '46': 'Routing loop detected',
    '47': 'Delivery time expired',

    '50': 'Other or undefined protocol status',
    '51': 'Invalid command',
    '52': 'Syntax error',
    '53': 'Too many recipients',
    '54': 'Invalid command arguments',
    '55': 'Wrong protocol version',

    '60': 'Other or undefined media error',
    '61': 'Media not supported',
    '62': 'Conversion required and prohibited',
    '63': 'Conversion required but not supported',
    '64': 'Conversion with loss performed',
    '65': 'Conversion failed',

    '70': 'Other or undefined security status',
    '71': 'Delivery not authorized, message refused',
    '72': 'Mailing list expansion prohibited',
    '73': 'Security conversion required but not possible',
    '74': 'Security features not supported',
    '75': 'Cryptographic failure',
    '76': 'Cryptographic algorithm not supported',
    '77': 'Message integrity failure',
}


def match_bounce_headers(msg):
    """
    Goes through the headers in a potential bounce message recursively
    and collects all the answers for the usual bounce headers.
    """
    matches = {'Content-Description-Parts': {}}
    for part in msg.base.walk():
        for k in BOUNCE_MATCHERS:
            if k in part:
                if k not in matches:
                    matches[k] = set()

                # kind of an odd place to put this, but it's the easiest way
                if k == 'Content-Description':
                    matches['Content-Description-Parts'][part[k].lower()] = part

                matches[k].add(part[k])

    return matches


def detect(msg):
    """
    Given a message, this will calculate a probability score based on
    possible bounce headers it finds and return a salmon.bounce.BounceAnalyzer
    object for further analysis.

    The detection algorithm is very simple but still accurate.  For each header
    it finds it adds a point to the score.  It then uses the regex in BOUNCE_MATCHERS
    to see if the value of that header is parsable, and if it is it adds another
    point to the score.  The final probability is based on how many headers and matchers
    were found out of the total possible.

    Finally, a header will be included in the score if it doesn't match in value, but
    it WILL NOT be included in the headers used by BounceAnalyzer to give you meanings
    like remote_mta and such.

    Because this algorithm is very dumb, you are free to add to BOUNCE_MATCHERS in your
    boot files if there's special headers you need to detect in your own code.
    """
    originals = match_bounce_headers(msg)
    results = {'Content-Description-Parts':
               originals['Content-Description-Parts']}
    score = 0
    del originals['Content-Description-Parts']

    for key in originals:
        score += 1  # score still goes up, even if value doesn't parse
        r = BOUNCE_MATCHERS[key]

        scan = (r.match(v) for v in originals[key])
        matched = [m.groups() for m in scan if m]

        # a key is counted in the score, but only added if it matches
        if len(matched) > 0:
            score += len(matched) / len(originals[key])
            results[key] = matched

    return BounceAnalyzer(results, score / BOUNCE_MAX)


class BounceAnalyzer:
    """
    BounceAnalyzer collects up the score and the headers and gives more
    meaningful interaction with them.  You can keep it simple and just use
    is_hard, is_soft, and probable methods to see if there was a bounce.
    If you need more information then attributes are set for each of the following:

        * primary_status -- The main status number that determines hard vs soft.
        * secondary_status -- Advice status.
        * combined_status -- the 2nd and 3rd number combined gives more detail.
        * remote_mta -- The MTA that you sent mail to and aborted.
        * reporting_mta -- The MTA that was sending the mail and has to report to you.
        * diagnostic_codes -- Human readable codes usually with info from the provider.
        * action -- Usually 'failed', and turns out to be not too useful.
        * content_parts -- All the attachments found as a hash keyed by the type.
        * original -- The original message, if it's found.
        * report -- All report elements, as salmon.encoding.MailBase raw messages.
        * notification -- Usually the detailed reason you bounced.
    """
    def __init__(self, headers, score):
        """
        Initializes all the various attributes you can use to analyze the bounce
        results.
        """
        self.headers = headers
        self.score = score

        if 'Status' in self.headers:
            status = self.headers['Status'][0]
            self.primary_status = int(status[0]), PRIMARY_STATUS_CODES[status[0]]
            self.secondary_status = int(status[1]), SECONDARY_STATUS_CODES[status[1]]
            combined = "".join(status[1:])
            self.combined_status = int(combined), COMBINED_STATUS_CODES[combined]
        else:
            self.primary_status = (None, None)
            self.secondary_status = (None, None)
            self.combined_status = (None, None)

        if 'Remote-Mta' in self.headers:
            self.remote_mta = self.headers['Remote-Mta'][0][1]
        else:
            self.remote_mta = None

        if 'Reporting-Mta' in self.headers:
            self.reporting_mta = self.headers['Reporting-Mta'][0][1]
        else:
            self.reporting_mta = None

        if 'Final-Recipient' in self.headers:
            self.final_recipient = self.headers['Final-Recipient'][0][1]
        else:
            self.final_recipient = None

        if 'Diagnostic-Code' in self.headers:
            self.diagnostic_codes = self.headers['Diagnostic-Code'][0][1:]
        else:
            self.diagnostic_codes = [None, None]

        if 'Action' in self.headers:
            self.action = self.headers['Action'][0][0]
        else:
            self.action = None

        # these are forced lowercase because they're so damn random
        self.content_parts = self.headers['Content-Description-Parts']
        # and of course, this isn't the original original, it's the wrapper
        self.original = self.content_parts.get('undelivered message', None)

        if self.original and self.original.parts:
            self.original = self.original.parts[0]

        self.report = self.content_parts.get('delivery report', None)
        if self.report and self.report.parts:
            self.report = self.report.parts

        self.notification = self.content_parts.get('notification', None)

    def is_hard(self):
        """
        Tells you if this was a hard bounce, which is determined by the message
        being a probably bounce with a primary_status greater than 4.
        """
        return self.probable() and self.primary_status[0] > 4

    def is_soft(self):
        """Basically the inverse of is_hard()"""
        return self.probable() and self.primary_status[0] <= 4

    def probable(self, threshold=0.3):
        """
        Determines if this is probably a bounce based on the score
        probability.  Default threshold is 0.3 which is conservative.
        """
        return self.score > threshold

    def error_for_humans(self):
        """
        Constructs an error from the status codes that you can print to
        a user.
        """
        if self.primary_status[0]:
            return "%s, %s, %s" % (self.primary_status[1],
                                   self.secondary_status[1],
                                   self.combined_status[1])
        else:
            return "No status codes found in bounce message."


class bounce_to:
    """
    Used to route bounce messages to a handler for either soft or hard bounces.
    Set the soft/hard parameters to the function that represents the handler.
    The function should take one argument of the message that it needs to handle
    and should have a route that handles everything.

    WARNING: You should only place this on the START of modules that will
    receive bounces, and every bounce handler should return START.  The reason
    is that the bounce emails come from *mail daemons* not the actual person
    who bounced.  You can find out who that person is using
    message.bounce.final_recipient.  But the bounce handler is *actually*
    interacting with a message from something like MAILER-DAEMON@somehost.com.
    If you don't go back to start immediately then you will mess with the state
    for this address, which can be bad.
    """
    def __init__(self, soft=None, hard=None):
        self.soft = soft
        self.hard = hard

        assert self.soft and self.hard, "You must give at least soft and/or hard"

    def __call__(self, func):
        @wraps(func)
        def bounce_wrapper(message, *args, **kw):
            if message.is_bounce():
                if message.bounce.is_soft():
                    return self.soft(message)
                else:
                    return self.hard(message)
            else:
                return func(message, *args, **kw)

        return bounce_wrapper
