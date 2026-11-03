"""A list entry's colour is checked before it is written into a ``style`` attribute.

Both packs' ``list_selection.html`` draw an entry's swatch as ``style="color: #`` followed by the
colour. Html-escaping is no defence there: the character that does the damage is a semicolon,
and escaping leaves it alone, so a stored ``f;position:fixed;inset:0`` arrived as a second
declaration and lifted the swatch out of the list and over the page. So ``add_list_entry`` keeps
a colour only when it is hex digits -- taking a leading ``#`` off, since the template writes its
own -- and drops anything else, which draws no swatch, as for an entry with no colour.
"""
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from cards.card_list.main import CardList, list_colour_digits
from cards_examples.models import Company
from cards_examples.tests.test_escaping import PACKS, _Page

STYLE_PAYLOAD = 'f;position:fixed;inset:0'


class TestListColourDigits(SimpleTestCase):

    def test_hex_colours_are_kept(self):
        for colour in ('fff', 'ffff', '90EE90', '90ee90cc'):
            with self.subTest(colour=colour):
                self.assertEqual(list_colour_digits(colour), colour)

    def test_a_leading_hash_is_taken_off(self):
        self.assertEqual(list_colour_digits('#90EE90'), '90EE90')

    def test_anything_else_is_dropped(self):
        for colour in (STYLE_PAYLOAD, 'red', '12345', 'ggg', '#', '', '90EE90;', 'x90EE90', '##fff'):
            with self.subTest(colour=colour):
                self.assertIsNone(list_colour_digits(colour))

    def test_surrounding_space_is_ignored(self):
        self.assertEqual(list_colour_digits(' 90EE90 '), '90EE90')

    def test_none_is_none(self):
        self.assertIsNone(list_colour_digits(None))


class _ColourList(CardList):
    model = Company

    def get_list_colour(self, entry_object):
        return entry_object.background_colour


class TestTheSwatchIsChecked(TestCase):

    def render_list(self):
        pages = {}
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                view = _ColourList()
                view.request = RequestFactory().get('/')
                view.display_list_entries()
                pages[pack] = view.add_list_card(list_entries=view.list_entries, card_name='list').render()
        return pages

    def swatches(self, html):
        return [attrs for attrs in _Page(html).find('i') if 'fa-square' in (attrs.get('class') or '')]

    def test_a_hex_colour_draws_a_swatch(self):
        Company.objects.create(name='Green', background_colour='#90EE90')
        for pack, html in self.render_list().items():
            with self.subTest(pack=pack):
                swatches = self.swatches(html)
                self.assertEqual(len(swatches), 1, html)
                self.assertIn('color: #90EE90;', swatches[0]['style'])

    def test_a_colour_that_is_not_one_draws_no_swatch(self):
        # SQLite does not enforce the field's max_length, so the whole payload is stored -- as a
        # colour column nothing validates would hold it.
        Company.objects.create(name='Over the page', background_colour=STYLE_PAYLOAD)
        for pack, html in self.render_list().items():
            with self.subTest(pack=pack):
                self.assertEqual(self.swatches(html), [], html)
                self.assertNotIn('position:fixed', html)
