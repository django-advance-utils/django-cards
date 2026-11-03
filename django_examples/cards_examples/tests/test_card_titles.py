"""A card's title is text unless it is marked safe, and a card remembers that it is empty.

``CardBase`` used to mark every title safe as it took it, so ``{{ card.title }}`` printed
whatever it was handed as markup, and a title made from stored text -- a company's name, a
product's -- ran as markup in the session of whoever opened the page. Now a title goes through
``escape_value``, the rule 1.7 gave a row's value and label: markup is marked safe where it is
made (``format_html``, ``mark_safe``, a rendered template or menu) and anything else is escaped.

The ``message`` template also printed the title with ``|safe``, so a title set on a card after
it was built bypassed the rule there and nowhere else. An empty card is routed to ``message``
whatever template it asked for, so that copy is checked through both doors.

The card's code is slugified from the title as it was passed, before the escaping, so a title
with an ``&`` in it keeps the code a page and its ajax reload address the card by.
"""
from django.test import SimpleTestCase, override_settings
from django.utils.html import format_html

from cards_examples.tests.test_escaping import ESCAPED_PAYLOAD, PACKS, PAYLOAD, _Page
from cards_examples.tests.test_show_header_message_table import CARDS, _view


def _default_card(**kwargs):
    card = _view().add_card(card_name='probe', **kwargs)
    card.add_entry(value='one', label='First')
    return card


def _html_card(**kwargs):
    return _view().add_html_data_card(card_name='probe', html='<p>body</p>', **kwargs)


ALL_CARDS = CARDS + (('default', _default_card), ('html', _html_card))


class TestATitleIsText(SimpleTestCase):

    def _for_each_card(self, check):
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                for name, build in ALL_CARDS:
                    with self.subTest(pack=pack, card=name):
                        check(build)

    def test_a_title_is_escaped(self):
        def check(build):
            html = build(title=PAYLOAD).render()
            self.assertEqual(_Page(html).find('img'), [], html)
            self.assertIn(ESCAPED_PAYLOAD, html)
        self._for_each_card(check)

    def test_a_title_marked_safe_is_markup(self):
        def check(build):
            html = build(title=format_html('<b class="made">{}</b>', 'Brass & Co')).render()
            self.assertEqual(len(_Page(html).find('b', **{'class': 'made'})), 1, html)
            self.assertIn('Brass &amp; Co', html)
        self._for_each_card(check)

    def test_the_message_template_does_not_mark_a_title_safe_itself(self):
        """A title assigned after the card is built has not been through the constructor."""
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                for name, build in (('message', CARDS[0][1]), ('empty', CARDS[1][1])):
                    with self.subTest(pack=pack, card=name):
                        card = build()
                        card.title = PAYLOAD
                        html = card.render()
                        self.assertEqual(_Page(html).find('img'), [], html)
                        self.assertIn(ESCAPED_PAYLOAD, html)

    def test_the_code_comes_from_the_title_as_it_was_passed(self):
        card = _view().add_card(title='R&D Details')
        self.assertEqual(card.code, 'rd_details_card')
        self.assertEqual(card.title, 'R&amp;D Details')

    def test_no_title_stays_none(self):
        self.assertIsNone(_view().add_card(card_name='probe').title)


class TestACardRemembersItIsEmpty(SimpleTestCase):
    """``is_empty`` used to pick the template and be dropped, so nothing could ask afterwards."""

    def test_an_empty_card_says_so(self):
        self.assertTrue(_view().add_card(card_name='probe', is_empty=True).is_empty)

    def test_a_card_with_content_says_so(self):
        self.assertFalse(_view().add_card(card_name='probe').is_empty)

    def test_an_empty_html_card_says_so(self):
        self.assertTrue(_view().add_html_data_card(card_name='probe', html=None, is_empty=True).is_empty)
