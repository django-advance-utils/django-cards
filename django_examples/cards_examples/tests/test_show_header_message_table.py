"""``message``, ``table`` and ``datatable`` cards honour ``show_header`` like the other body templates.

``default`` and ``html`` wrap their header in ``{% if show_header %}``; ``message`` keyed on
``card.title`` alone and ``table`` never looked, so a card built with ``show_header=False`` still
drew its header through either. That bit twice: a table-template card cannot be folded into a
larger card as a headerless section, and an *empty* card (``is_empty=True``) is routed to the
``message`` template whatever template the caller asked for, keeping its own title -- so a
consumer that had switched the header off on a card with nothing to show got one anyway.

``datatable`` and ``linked_datatables`` never looked either, so a datatable card could not be
folded away as a headerless section any more than a table one could. Their guard closes before
``card.tab_menu.render``: a headerless card keeps its tab bar.

``message`` keeps its title check inside the switch: a titleless message card (an alert with no
heading) draws no header, exactly as before.

Rendered through ``CardMixin`` rather than ``render_to_string`` with a stand-in, because every one
of these cards builds without a database (a datatable's rows arrive by ajax, so rendering one
queries nothing) and the routing of an empty card onto ``message`` is part of what is asserted.
Each pack has its own copy of every template here, so the cards are built under both.
"""
from cards.base import CARD_TYPE_DATATABLE
from cards.standard import CardMixin
from cards_examples.models import Company
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.views.generic import TemplateView

#: The opening tag, not the bare class: the shared stylesheet mentions `card-header` too.
HEADER = '<div class="card-header'
PACKS = ('bootstrap4', 'bootstrap5')


class _CardView(CardMixin, TemplateView):
    def setup_table(self, table, details_object):
        # Rows by ajax, as a page's datatable takes them: rendering the card then queries nothing.
        table.ajax_data = True
        table.add_columns('id', 'name')


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


def _datatable_card(**kwargs):
    kwargs.setdefault('title', 'Probe datatable')
    return _view().add_card(card_name='probe', group_type=CARD_TYPE_DATATABLE, datatable_model=Company, **kwargs)


def _linked_card(**kwargs):
    kwargs.setdefault('title', 'Probe linked')
    return _view().add_linked_datatables_card(
        card_name='probe', datatables=[{'id': 'companies', 'model': Company, 'title': 'Companies'}], **kwargs)


CARDS = (
    ('message', _message_card),
    ('empty', _empty_card),
    ('table', _table_card),
    ('datatable', _datatable_card),
    ('linked', _linked_card),
)


class TestMessageTableAndDatatableShowHeader(SimpleTestCase):
    def _for_each_card(self, check):
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                for name, build in CARDS:
                    with self.subTest(pack=pack, card=name):
                        check(name, build)

    def test_show_header_off_draws_no_header(self):
        def check(name, build):
            self.assertNotIn(HEADER, build(show_header=False).render())
        self._for_each_card(check)

    def test_the_default_still_draws_the_header(self):
        def check(name, build):
            html = build().render()
            self.assertIn(HEADER, html)
            self.assertIn(f'Probe {name}', html)
        self._for_each_card(check)

    def test_a_titleless_message_card_still_draws_no_header(self):
        """The inner condition is kept: show_header on is not, by itself, a reason for a header."""
        self.assertNotIn(HEADER, _message_card(title=None).render())

    def test_the_body_survives_losing_the_header(self):
        self.assertIn('Nothing to see', _message_card(show_header=False).render())
        self.assertIn('No data', _empty_card(show_header=False).render())
        self.assertIn('First', _table_card(show_header=False).render())
        self.assertIn('id="probe"', _datatable_card(show_header=False).render())
        self.assertIn('id="companies"', _linked_card(show_header=False).render())
