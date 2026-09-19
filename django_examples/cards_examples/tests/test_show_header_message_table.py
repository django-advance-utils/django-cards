"""``message`` and ``table`` cards honour ``show_header`` like the other body templates.

``default`` and ``html`` wrap their header in ``{% if show_header %}``; ``message`` keyed on
``card.title`` alone and ``table`` never looked, so a card built with ``show_header=False`` still
drew its header through either. That bit twice: a table-template card cannot be folded into a
larger card as a headerless section, and an *empty* card (``is_empty=True``) is routed to the
``message`` template whatever template the caller asked for, keeping its own title -- so a
consumer that had switched the header off on a card with nothing to show got one anyway.

``message`` keeps its title check inside the switch: a titleless message card (an alert with no
heading) draws no header, exactly as before.

Rendered through ``CardMixin`` rather than ``render_to_string`` with a stand-in, because both cards
build without a database or a datatable and the routing of an empty card onto ``message`` is part
of what is asserted.
"""
from cards.standard import CardMixin
from django.test import RequestFactory, SimpleTestCase
from django.views.generic import TemplateView

#: The opening tag, not the bare class: the shared stylesheet mentions `card-header` too.
HEADER = '<div class="card-header'


class _CardView(CardMixin, TemplateView):
    pass


def _view():
    view = _CardView()
    view.request = RequestFactory().get('/')
    return view


def _message_card(**kwargs):
    kwargs.setdefault('title', 'Probe message')
    return _view().add_message_card(card_name='probe', message='Nothing to see', **kwargs)


def _empty_card(**kwargs):
    """A card that asked for the default template and was sent to ``message`` for being empty."""
    kwargs.setdefault('title', 'Probe empty')
    return _view().add_card(card_name='probe', is_empty=True, empty_message='No data', **kwargs)


def _table_card(**kwargs):
    kwargs.setdefault('title', 'Probe table')
    card = _view().add_card(card_name='probe', template_name='table', **kwargs)
    card.add_entry(value='one', label='First')
    return card


class TestMessageAndTableShowHeader(SimpleTestCase):
    def test_show_header_off_draws_no_header(self):
        for name, build in (('message', _message_card), ('empty', _empty_card), ('table', _table_card)):
            with self.subTest(card=name):
                self.assertNotIn(HEADER, build(show_header=False).render())

    def test_the_default_still_draws_the_header(self):
        for name, build in (('message', _message_card), ('empty', _empty_card), ('table', _table_card)):
            with self.subTest(card=name):
                html = build().render()
                self.assertIn(HEADER, html)
                self.assertIn(f'Probe {name}', html)

    def test_a_titleless_message_card_still_draws_no_header(self):
        """The inner condition is kept: show_header on is not, by itself, a reason for a header."""
        self.assertNotIn(HEADER, _message_card(title=None).render())

    def test_the_body_survives_losing_the_header(self):
        self.assertIn('Nothing to see', _message_card(show_header=False).render())
        self.assertIn('No data', _empty_card(show_header=False).render())
        self.assertIn('First', _table_card(show_header=False).render())
