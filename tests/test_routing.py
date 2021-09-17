from unittest.mock import MagicMock, Mock, patch

from salmon import routing
from salmon.mail import MailRequest
from salmon.routing import (MemoryStorage, Router, ShelveStorage, StateStorage, has_salmon_settings, locking, nolocking,
                            route, route_like, salmon_setting)

from .handlers import simple_fsm_mod
from .setup_env import SalmonTestCase, setup_router


class RoutingTestCase(SalmonTestCase):
    def setUp(self):
        super().setUp()
        setup_router(['tests.handlers.simple_fsm_mod'])

    def test_MemoryStorage(self):
        store = MemoryStorage()
        store.set(self.__module__, "tester@localhost", "TESTED")

        self.assertEqual(store.get(self.__module__, "tester@localhost"), "TESTED")

        self.assertEqual(store.get(self.__module__, "tester2@localhost"), "START")

        store.clear()

        self.assertEqual(store.get(self.__module__, "tester@localhost"), "START")

    def test_ShelveStorage(self):
        store = ShelveStorage("run/states.db")

        store.set(self.__module__, "tester@localhost", "TESTED")
        self.assertEqual(store.get(self.__module__, "tester@localhost"), "TESTED")

        self.assertEqual(store.get(self.__module__, "tester2@localhost"), "START")

        store.clear()
        self.assertEqual(store.get(self.__module__, "tester@localhost"), "START")

    def test_RoutingBase(self):
        Router.clear_routes()
        Router.clear_states()
        Router.HANDLERS.clear()

        # check that Router is in a pristine state
        self.assertEqual(len(Router.ORDER), 0)
        self.assertEqual(len(Router.REGISTERED), 0)

        setup_router(['tests.handlers.simple_fsm_mod'])

        self.assertEqual(len(Router.ORDER), 4)
        self.assertEqual(len(Router.REGISTERED), 4)

        message = MailRequest('fakepeer', 'zedshaw@localhost', 'users-subscribe@localhost', "")
        Router.deliver(message)
        assert Router.in_state(simple_fsm_mod.CONFIRM, message)

        confirm = MailRequest('fakepeer', '"Zed Shaw" <zedshaw@localhost>',  'users-confirm-1@localhost', "")
        Router.deliver(confirm)
        assert Router.in_state(simple_fsm_mod.POSTING, message)

        Router.deliver(message)
        assert Router.in_state(simple_fsm_mod.NEXT, message)

        Router.deliver(message)
        assert Router.in_state(simple_fsm_mod.END, message)

        Router.deliver(message)
        assert Router.in_state(simple_fsm_mod.START, message)

        Router.clear_states()
        Router.LOG_EXCEPTIONS = True
        explosion = MailRequest('fakepeer', '<hacker@localhost>', 'start-explode@localhost', "")
        Router.deliver(explosion)

        assert Router.in_error(simple_fsm_mod.END, explosion)

        Router.clear_states()
        Router.LOG_EXCEPTIONS = False
        explosion = MailRequest('fakepeer',  'hacker@localhost', 'start-explode@localhost', "")
        with self.assertRaises(RuntimeError):
            Router.deliver(explosion)

        Router.reload()
        assert 'tests.handlers.simple_fsm_mod' in Router.HANDLERS
        self.assertEqual(len(Router.ORDER), 4)
        self.assertEqual(len(Router.REGISTERED), 4)

    def test_Router_undeliverable_queue(self):
        Router.clear_routes()
        Router.clear_states()

        Router.UNDELIVERABLE_QUEUE = Mock()
        msg = MailRequest('fakepeer', 'from@localhost', 'to@localhost', "Nothing")

        Router.deliver(msg)
        self.assertEqual(Router.UNDELIVERABLE_QUEUE.push.call_count, 1)

    def test_StateStorage_get_raises(self):
        s = StateStorage()
        with self.assertRaises(NotImplementedError):
            s.get("raises", "raises")

    def test_StateStorage_set_raises(self):
        s = StateStorage()
        with self.assertRaises(NotImplementedError):
            s.set("raises", "raises", "raises")

    def test_StateStorage_clear_raises(self):
        s = StateStorage()
        with self.assertRaises(NotImplementedError):
            s.clear()

    def test_route___get___raises(self):
        class BadRoute:

            @route("test")
            def wont_work(message, **kw):
                pass

        br = BadRoute()
        with self.assertRaises(TypeError):
            br.wont_work("raises")

    @patch('salmon.routing.reload', new=Mock(side_effect=ImportError))
    @patch('salmon.routing.LOG', new=Mock())
    def test_reload_raises(self):
        Router.LOG_EXCEPTIONS = True
        Router.reload()
        self.assertEqual(routing.LOG.exception.call_count, 1)

        Router.LOG_EXCEPTIONS = False
        routing.LOG.exception.reset_mock()
        with self.assertRaises(ImportError):
            Router.reload()
        self.assertEqual(routing.LOG.exception.call_count, 0)

        routing.LOG.exception.reset_mock()
        Router.LOG_EXCEPTIONS = True
        Router.load(['fake.handler'])
        self.assertEqual(routing.LOG.exception.call_count, 1)

        Router.LOG_EXCEPTIONS = False
        routing.LOG.exception.reset_mock()
        with self.assertRaises(ImportError):
            Router.load(['fake.handler'])
        self.assertEqual(routing.LOG.exception.call_count, 0)

    def test_route_like_typeerror(self):
        def func():
            pass

        with self.assertRaises(TypeError):
            route_like(func)

    def test_locking_decorator(self):
        def func():
            pass

        new_func = locking(func)
        self.assertTrue(has_salmon_settings(new_func))
        self.assertTrue(salmon_setting(new_func, "locking"))

    def test_nolocking_decorator(self):
        def func():
            pass

        with self.assertWarns(DeprecationWarning):
            new_func = nolocking(func)
        self.assertFalse(has_salmon_settings(new_func))
        self.assertIsNone(salmon_setting(new_func, "locking"))

    def test_locking_locks_router(self):
        Router.clear_routes()
        Router.clear_states()
        Router.HANDLERS.clear()

        @route(".*")
        @locking
        def START(message):
            pass

        message = MailRequest('peer', 'me@localhost', 'you@localhost', "")
        with patch.object(Router, "call_lock", new=MagicMock()) as lock_mock:
            Router.deliver(message)
            self.assertEqual(lock_mock.__enter__.call_count, 1)

    def test_no_locks_router(self):
        Router.clear_routes()
        Router.clear_states()
        Router.HANDLERS.clear()

        @route(".*")
        def START(message):
            pass

        message = MailRequest('peer', 'me@localhost', 'you@localhost', "")
        with patch.object(Router, "call_lock", new=MagicMock()) as lock_mock:
            Router.deliver(message)
            self.assertEqual(lock_mock.__enter__.call_count, 0)
