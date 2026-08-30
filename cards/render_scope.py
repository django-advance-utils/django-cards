"""Somewhere to record "the page has already carried this" while a request is being served.

A card usually knows its own request and can mark it, but not always: a form widget that
builds its own card mixin has no request to hand it, and a modal holding four such widgets is
exactly the page that most needs its shared assets emitted once. So keep a marker object per
request cycle here instead.

Outside a request cycle there is no scope, and callers have to read that as "emit it again".
Erring the other way would leave a page carrying no behaviour at all, which is a broken page
rather than a large one.

One environment caveat: contextvars isolate per thread and per asyncio task, which covers
threaded WSGI and ASGI, but greenlet servers that do not patch contextvars (gunicorn's
eventlet worker) share one context across the requests interleaved on a thread, so the scope
-- and the dedupe marks on it -- can bleed between them there.
"""
import contextvars

from django.core.signals import request_finished, request_started

_current_scope = contextvars.ContextVar('cards_render_scope', default=None)


class RenderScope:
    """Per-request-cycle flags. Whoever needs one sets an attribute on it."""


def get_render_scope():
    """The scope for the request being served, or None outside a request cycle."""
    return _current_scope.get()


def _open_scope(**kwargs):
    _current_scope.set(RenderScope())


def _close_scope(**kwargs):
    _current_scope.set(None)


def connect_signals():
    """Called from the app's ready(); safe to call more than once."""
    request_started.connect(_open_scope, dispatch_uid='cards_render_scope_open')
    request_finished.connect(_close_scope, dispatch_uid='cards_render_scope_close')
