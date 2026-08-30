"""The render scope has to survive the ASGI shape: request_started fires on the event loop,
then a sync view runs in a thread from the pool. jms_cloud serves through daphne, so this is
the path that matters, and a scope that did not reach the view -- or worse, one left over from
a previous request on a reused worker thread -- would be a broken page rather than a large one.
"""
import asyncio
import threading

from asgiref.sync import sync_to_async
from django.core.signals import request_finished, request_started
from django.test import TestCase

from cards.render_scope import get_render_scope


class TestRenderScopeAcrossThreads(TestCase):

    def test_scope_set_on_the_loop_reaches_a_sync_view_in_the_pool(self):
        seen = {}

        def sync_view():
            seen['thread'] = threading.current_thread().name
            scope = get_render_scope()
            seen['scope'] = scope
            if scope is not None:
                scope.touched = True

        async def one_request():
            request_started.send(sender=self.__class__)
            seen['loop_scope'] = get_render_scope()
            await sync_to_async(sync_view)()
            request_finished.send(sender=self.__class__)
            return get_render_scope()

        after = asyncio.run(one_request())
        self.assertIsNotNone(seen['loop_scope'], 'the signal opened no scope')
        self.assertIs(seen['scope'], seen['loop_scope'],
                      'the view thread saw a different scope from the loop')
        self.assertTrue(getattr(seen['loop_scope'], 'touched', False),
                        'a flag set in the view thread was not visible on the scope')
        self.assertIsNone(after, 'request_finished left the scope open')
        self.assertNotEqual(seen['thread'], threading.current_thread().name)

    def test_two_requests_do_not_share_a_scope(self):
        scopes = []

        async def one_request():
            request_started.send(sender=self.__class__)
            await sync_to_async(lambda: scopes.append(get_render_scope()))()
            request_finished.send(sender=self.__class__)

        async def both():
            await asyncio.gather(one_request(), one_request())

        asyncio.run(both())
        self.assertEqual(len(scopes), 2)
        self.assertIsNotNone(scopes[0])
        self.assertIsNot(scopes[0], scopes[1])

    def test_a_worker_thread_does_not_keep_the_previous_scope(self):
        """Whatever the pool reuses, the scope comes from the request being served."""
        seen = []

        async def one_request(open_scope):
            if open_scope:
                request_started.send(sender=self.__class__)
            await sync_to_async(lambda: seen.append(get_render_scope()))()
            if open_scope:
                request_finished.send(sender=self.__class__)

        asyncio.run(one_request(True))
        asyncio.run(one_request(False))
        self.assertIsNotNone(seen[0])
        self.assertIsNone(seen[1], 'a scope leaked into a render with no request cycle')
