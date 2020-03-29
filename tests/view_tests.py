from unittest import TestCase

from salmon import view
import jinja2


class ViewsTestCase(TestCase):
    def setUp(self):
        view.LOADER = jinja2.Environment(loader=jinja2.FileSystemLoader('tests/data/templates'))

    def tearDown(self):
        view.LOADER = None

    def test_load(self):
        template = view.load("template.txt")
        assert template
        assert template.render()

    def test_render(self):
        # try with some empty vars
        text = view.render({}, "template.txt")
        assert text

    def test_most_basic_form(self):
        msg = view.respond(locals(), 'template.txt')
        assert msg.Body

    def test_respond_cadillac_version(self):
        person = 'Tester'

        msg = view.respond(locals(), Body='template.txt', Html='template.html', From='test@localhost',
                           To='receiver@localhost', Subject='Test body from "%(person)s".')

        assert msg.Body
        assert msg.Html

        for k in ['From', 'To', 'Subject']:
            assert k in msg

    def test_respond_plain_text(self):
        person = 'Tester'

        msg = view.respond(locals(), Body='template.txt', From='test@localhost', To='receiver@localhost',
                           Subject='Test body from "%(person)s".')

        assert msg.Body
        assert not msg.Html

        for k in ['From', 'To', 'Subject']:
            assert k in msg

    def test_respond_html_only(self):
        person = 'Tester'

        msg = view.respond(locals(), Html='template.html', From='test@localhost', To='receiver@localhost',
                           Subject='Test body from "%(person)s".')

        assert not msg.Body
        assert msg.Html

        for k in ['From', 'To', 'Subject']:
            assert k in msg

    def test_respond_attach(self):
        person = "hello"
        mail = view.respond(locals(), Body="template.txt", From="test@localhost", To="receiver@localhost",
                            Subject='Test body from someone.')

        view.attach(mail, locals(), 'template.html', content_type="text/html", filename="template.html",
                    disposition='attachment')

        self.assertEqual(len(mail.attachments), 1)

        msg = mail.to_message()
        self.assertEqual(len(msg.get_payload()), 2)
        assert str(msg)

        mail.clear()

        view.attach(mail, locals(), 'template.html', content_type="text/html")
        self.assertEqual(len(mail.attachments), 1)

        msg = mail.to_message()
        self.assertEqual(len(msg.get_payload()), 2)
        assert str(msg)

    def test_unicode(self):
        person = u'H\xe9avy M\xe9t\xe5l Un\xeec\xf8d\xe9'
        mail = view.respond(locals(), Html="unicode.html", From="test@localhost", To="receiver@localhost",
                            Subject='Test body from someone.')

        assert str(mail)

        view.attach(mail, locals(), "unicode.html", filename="attached.html")

        assert str(mail)
