# Copyright (C) 2008 Zed A. Shaw.  Licensed under the terms of the GPLv3.
from __future__ import print_function

from unittest import TestCase

from salmon import encoding, mail

sample_message = """From: somedude@localhost
To: somedude@localhost

Test
"""


class MessageTestCase(TestCase):
    def test_mail_request(self):
        # try with a half-assed message
        msg = mail.MailRequest("localhost", "zedfrom@localhost",
                               "zedto@localhost", "Fake body.")
        self.assertEqual(msg['to'], "zedto@localhost")
        self.assertEqual(msg['from'], "zedfrom@localhost")

        msg = mail.MailRequest("localhost", "somedude@localhost", ["somedude@localhost"], sample_message)
        self.assertEqual(msg.original, sample_message)

        self.assertEqual(msg['From'], "somedude@localhost")

        assert("From" in msg)
        del msg["From"]
        assert("From" not in msg)

        msg["From"] = "nobody@localhost"
        assert("From" in msg)
        self.assertEqual(msg["From"], "nobody@localhost")
        msg["From"] = "somebody@localhost"
        self.assertEqual(msg["From"], "somebody@localhost")
        self.assertEqual(msg.keys(), ["To", "From"])
        self.assertEqual(msg.items(), [("To", "somedude@localhost"), ("From", "somebody@localhost")])

        # appending headers
        msg.base.append_header("To", "nobody@example.com")
        self.assertEqual(msg["To"], "somedude@localhost")
        self.assertEqual(msg.keys(), ["To", "From", "To"])
        self.assertEqual(msg.items(), [("To", "somedude@localhost"), ("From", "somebody@localhost"),
                                       ("To", "nobody@example.com")])

        # validate that upper and lower case work for headers
        assert("FroM" in msg)
        assert("from" in msg)
        assert("From" in msg)
        self.assertEqual(msg['From'], msg['fRom'])
        self.assertEqual(msg['From'], msg['from'])
        self.assertEqual(msg['from'], msg['fRom'])

        # make sure repr runs
        assert repr(msg)

        assert str(msg)

    def test_mail_response_plain_text(self):
        sample = mail.MailResponse(
            To="receiver@localhost",
            Subject="Test message",
            From="sender@localhost",
            Body="Test from test_mail_response_plain_text.",
        )

        assert str(sample)
        return sample

    def test_mail_response_html(self):
        sample = mail.MailResponse(
            To="receiver@localhost",
            Subject="Test message",
            From="sender@localhost",
            Html="<html><body><p>From test_mail_response_html</p></body></html>",
        )

        assert str(sample)
        return sample

    def test_mail_response_html_and_plain_text(self):
        sample = mail.MailResponse(
            To="receiver@localhost",
            Subject="Test message",
            From="sender@localhost",
            Html="<html><body><p>Hi there.</p></body></html>",
            Body="Test from test_mail_response_html_and_plain_text.",
        )

        assert str(sample)
        return sample

    def test_mail_response_attachments(self):
        sample = mail.MailResponse(
            To="receiver@localhost",
            Subject="Test message",
            From="sender@localhost",
            Body="Test from test_mail_response_attachments.",
        )
        with open("./README.rst") as file_obj:
            readme_data = file_obj.read()

        with self.assertRaises(AssertionError):
            sample.attach(data=readme_data, disposition="inline")

        sample.attach(filename="./README.rst", content_type="text/plain", disposition="inline")
        self.assertEqual(len(sample.attachments), 1)
        assert sample.multipart

        msg = sample.to_message()
        self.assertEqual(len(msg.get_payload()), 2)

        sample.clear()
        self.assertEqual(len(sample.attachments), 0)
        assert not sample.multipart

        sample.attach(data=readme_data, filename="./README.rst", content_type="text/plain")

        msg = sample.to_message()
        self.assertEqual(len(msg.get_payload()), 2)
        sample.clear()

        sample.attach(data=readme_data, content_type="text/plain")
        msg = sample.to_message()
        self.assertEqual(len(msg.get_payload()), 2)

        assert str(sample)
        return sample

    def test_mail_request_attachments(self):
        sample = self.test_mail_response_attachments()
        data = str(sample)

        msg = mail.MailRequest("localhost", None, None, data)

        msg_parts = msg.all_parts()
        sample_parts = sample.all_parts()

        with open("./README.rst") as file_obj:
            readme = file_obj.read()

        assert msg_parts[0].body == sample_parts[0].body
        assert readme == msg_parts[1].body
        assert msg.body() == sample_parts[0].body

        # test that we get at least one message for messages without attachments
        sample = self.test_mail_response_plain_text()
        msg = mail.MailRequest("localhost", None, None, str(sample))
        msg_parts = msg.all_parts()
        self.assertEqual(len(msg_parts), 0)
        assert msg.body()

    def test_mail_response_mailing_list_headers(self):
        list_addr = "test.users@localhost"

        msg = mail.MailResponse(From='somedude@localhost', To=list_addr, Subject='subject', Body="Mailing list reply.")

        print(repr(msg))

        msg["Sender"] = list_addr
        msg["Reply-To"] = list_addr
        msg["List-Id"] = list_addr
        msg["Return-Path"] = list_addr
        msg["In-Reply-To"] = 'Message-Id-1231123'
        msg["References"] = 'Message-Id-838845854'
        msg["Precedence"] = 'list'

        data = str(msg)

        req = mail.MailRequest('localhost', 'somedude@localhost', list_addr, data)

        headers = ['Sender', 'Reply-To', 'List-Id', 'Return-Path', 'In-Reply-To', 'References', 'Precedence']
        for header in headers:
            assert msg[header] == req[header], "%s: %r != %r" % (header, msg[header], req[header])

        # try a delete
        del msg['Precedence']

    def test_mail_response_headers(self):
        msg = self.test_mail_response_plain_text()
        # validate that upper and lower case work for headers
        assert("FroM" in msg)
        assert("from" in msg)
        assert("From" in msg)
        self.assertEqual(msg['From'], msg['fRom'])
        self.assertEqual(msg['From'], msg['from'])
        self.assertEqual(msg['from'], msg['fRom'])

        self.assertEqual(msg.keys(), [i[0] for i in msg.items()])

    def test_walk(self):
        with open("tests/data/bounce.msg") as file_obj:
            bm = mail.MailRequest(None, None, None, file_obj.read())
        parts = [x for x in bm.walk()]

        assert parts
        self.assertEqual(len(parts), 6)

    def test_copy_parts(self):
        with open("tests/data/bounce.msg") as file_obj:
            bm = mail.MailRequest(None, None, None, file_obj.read())

        resp = mail.MailResponse(To=bm['to'], From=bm['from'], Subject=bm['subject'])

        resp.attach_all_parts(bm)

        resp = resp.to_message()
        bm = bm.to_message()

        self.assertEqual(len([x for x in bm.walk()]), len([x for x in resp.walk()]))

    def test_craft_from_sample(self):
        list_name = "test.list"
        user_full_address = "tester@localhost"

        sample = mail.MailResponse(
            To=list_name + "@localhost",
            From=user_full_address,
            Subject="Test message with attachments.",
            Body="The body as one attachment.",
        )
        sample.update({"Test": "update"})

        sample.attach(filename="tests/message_tests.py", content_type="text/plain", disposition="attachment")

        inmsg = mail.MailRequest("fakepeer", None, None, str(sample))
        assert "Test" in sample.keys()

        for part in inmsg.to_message().walk():
            assert part.get_payload(), "inmsg busted."

        outmsg = mail.MailResponse(To=inmsg['from'], From=inmsg['to'], Subject=inmsg['subject'])

        outmsg.attach_all_parts(inmsg)

        result = outmsg.to_message()

        for part in result.walk():
            assert part.get_payload(), "outmsg parts don't have payload."

    def test_to_from_works(self):
        msg = mail.MailRequest("fakepeer", "from@localhost", [u"<to1@localhost>", u"to2@localhost"], "")
        assert '<' not in msg.To, msg.To

        msg = mail.MailRequest("fakepeer", "from@localhost", [u"to1@localhost", u"to2@localhost"], "")
        assert '<' not in msg.To, msg.To

        msg = mail.MailRequest("fakepeer", "from@localhost", [u"to1@localhost", u"<to2@localhost>"], "")
        assert '<' not in msg.To, msg.To

        msg = mail.MailRequest("fakepeer", "from@localhost", [u"to1@localhost"], "")
        assert '<' not in msg.To, msg.To

        msg = mail.MailRequest("fakepeer", "from@localhost", [u"<to1@localhost>"], "")
        assert '<' not in msg.To, msg.To

    def test_decode_header_randomness(self):
        self.assertEqual(mail._decode_header_randomness(None), set())

        # with strings
        self.assertEqual(mail._decode_header_randomness(["z@localhost", '"Z A" <z@localhost>']),
                         set(["z@localhost", "z@localhost"]))
        self.assertEqual(mail._decode_header_randomness("z@localhost"), set(["z@localhost"]))

        # with bytes
        self.assertEqual(mail._decode_header_randomness([b"z@localhost", b'"Z A" <z@localhost>']),
                         set(["z@localhost", "z@localhost"]))
        self.assertEqual(mail._decode_header_randomness(b"z@localhost"), set(["z@localhost"]))

        # with literal nonsense
        with self.assertRaises(encoding.EncodingError):
            mail._decode_header_randomness(1)
        with self.assertRaises(encoding.EncodingError):
            mail._decode_header_randomness([1, "m@localhost"])
