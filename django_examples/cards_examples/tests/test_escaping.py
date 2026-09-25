"""A row's value and label are text unless they are marked safe.

Cards used to print every row's value and label with ``|safe``, and to mark every CardList
entry name safe, so stored text that reached a row or a list -- a product's name read with
``add_rows('name')``, a note, a many-to-many's names -- ran as markup in the session of whoever
opened the page. Now they are escaped unless they are marked safe (``mark_safe``,
``format_html``, a rendered template), both where the pack templates print a row and where the
card builds markup around a value itself: ``html_override``, a row style, the many-to-many
badges and a merged row. What the card itself draws -- the boolean icons, a sparkline,
auto-linked URLs -- is marked safe where it is made.

Every case renders through both packs and both row templates. The escaping lives in four copies
of two templates, and a copy left printing ``|safe`` would be silent on the pack a reader
happened to be looking at.

Markup is checked by parsing the page, not by looking for a string: the question is whether
stored text became an element, and a substring can be present in escaped form or absent from a
rewritten one without answering it.
"""
from html.parser import HTMLParser

from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.utils.functional import lazy
from django.utils.html import format_html
from django.utils.safestring import SafeString, mark_safe
from django.views.generic import TemplateView
from django_menus.menu import HtmlMenuItem

from cards.base import escape_value
from cards.card_list.main import CardList
from cards.standard import CardMixin
from cards_examples.models import Company, Sector

PAYLOAD = '<img src=x onerror=alert(1)>'
ESCAPED_PAYLOAD = '&lt;img src=x onerror=alert(1)&gt;'

PACKS = ('bootstrap4', 'bootstrap5')
ROW_TEMPLATES = ('default', 'table')


class _Page(HTMLParser):
    """The elements and the text of a rendered card."""

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.text = []
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

    handle_startendtag = handle_starttag

    def handle_data(self, data):
        self.text.append(data)

    def find(self, tag, **attrs):
        return [a for t, a in self.elements
                if t == tag and all(a.get(k) == v for k, v in attrs.items())]


class _CardView(CardMixin, TemplateView):
    pass


class _RenderEverywhere:
    """Build a card once per pack and row template, and hand back each rendering."""

    def render_everywhere(self, build, **card_kwargs):
        pages = {}
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                for template_name in ROW_TEMPLATES:
                    view = _CardView()
                    view.request = RequestFactory().get('/')
                    card = view.add_card('demo', title='Demo', template_name=template_name, **card_kwargs)
                    build(card)
                    pages[(pack, template_name)] = card.render()
        return pages

    def assert_escaped_everywhere(self, build, **card_kwargs):
        """The payload reaches every rendering as text, and never as an element."""
        for (pack, template_name), html in self.render_everywhere(build, **card_kwargs).items():
            with self.subTest(pack=pack, template=template_name):
                page = _Page(html)
                self.assertEqual(page.find('img'), [], html)
                self.assertIn(ESCAPED_PAYLOAD, html)
                self.assertIn(PAYLOAD, ''.join(page.text))


class TestValuesAndLabelsAreText(_RenderEverywhere, SimpleTestCase):

    def test_a_value_is_escaped(self):
        self.assert_escaped_everywhere(lambda card: card.add_entry(value=PAYLOAD, label='Name'))

    def test_a_label_is_escaped(self):
        self.assert_escaped_everywhere(lambda card: card.add_entry(value='Brass', label=PAYLOAD))

    def test_a_field_read_off_the_details_object_is_escaped(self):
        # The case that ran in the field: a name typed by one tenant, read by add_rows('name')
        # on a page another tenant opens.
        self.assert_escaped_everywhere(lambda card: card.add_rows('name'),
                                       details_object=Company(name=PAYLOAD))

    def test_each_line_of_a_list_value_is_escaped(self):
        self.assert_escaped_everywhere(lambda card: card.add_entry(value=[PAYLOAD, 'second'], label='Lines'))

    def test_a_default_is_escaped(self):
        self.assert_escaped_everywhere(lambda card: card.add_entry(value=None, default=PAYLOAD, label='Name'))

    def test_a_value_marked_safe_is_markup(self):
        for key, html in self.render_everywhere(
                lambda card: card.add_entry(value=format_html('<b class="made">{}</b>', 'Brass'), label='Name')).items():
            with self.subTest(pack=key[0], template=key[1]):
                self.assertEqual(len(_Page(html).find('b', **{'class': 'made'})), 1, html)

    def test_a_label_marked_safe_is_markup(self):
        for key, html in self.render_everywhere(
                lambda card: card.add_entry(value='10', label=mark_safe('Width &times; <sup>2</sup>'))).items():
            with self.subTest(pack=key[0], template=key[1]):
                self.assertIn('Width &times; <sup>2</sup>', html)

    def test_a_list_keeps_its_safe_lines_as_markup(self):
        for key, html in self.render_everywhere(
                lambda card: card.add_entry(value=[mark_safe('<b class="made">1</b>'), PAYLOAD], label='Lines')).items():
            with self.subTest(pack=key[0], template=key[1]):
                page = _Page(html)
                self.assertEqual(len(page.find('b', **{'class': 'made'})), 1, html)
                self.assertEqual(page.find('img'), [], html)

    def test_an_object_whose_str_is_safe_markup_stays_markup(self):
        # html_classes elements return mark_safe(...) from __str__ and carry no __html__, which
        # is how {{ }} treats them too: str() first, then escape unless safe.
        class Element:
            def __str__(self):
                return mark_safe('<span class="element">made</span>')

        for key, html in self.render_everywhere(lambda card: card.add_entry(value=Element(), label='E')).items():
            with self.subTest(pack=key[0], template=key[1]):
                self.assertEqual(len(_Page(html).find('span', **{'class': 'element'})), 1, html)

    def test_a_value_is_escaped_once(self):
        # Escaped in the template and nowhere else, so an ampersand reads as one.
        for key, html in self.render_everywhere(lambda card: card.add_entry(value='Smith & Sons', label='N')).items():
            with self.subTest(pack=key[0], template=key[1]):
                self.assertIn('Smith &amp; Sons', html)
                self.assertNotIn('&amp;amp;', html)

    def test_copy_to_clipboard_copies_the_text_as_it_was_typed(self):
        # The escaping is the template's, so the value the clipboard button is handed is still
        # the text: writeText gets 'a & <b>', not 'a &amp; &lt;b&gt;'.
        for key, html in self.render_everywhere(
                lambda card: card.add_entry(value='a & <b>', label='N', copy_to_clipboard=True)).items():
            with self.subTest(pack=key[0], template=key[1]):
                onclick = [a['onclick'] for _, a in _Page(html).elements if 'onclick' in a]
                self.assertEqual(onclick, ["navigator.clipboard.writeText('a \\u0026 \\u003Cb\\u003E')"])

    def test_an_html_row_is_markup_by_contract(self):
        # add_html_string_entry and add_html_entry take markup; nothing about that changed.
        for key, html in self.render_everywhere(
                lambda card: card.add_html_string_entry('<div class="raw">x</div>', exclude_td=False)).items():
            with self.subTest(pack=key[0], template=key[1]):
                self.assertEqual(len(_Page(html).find('div', **{'class': 'raw'})), 1, html)


class TestMarkupTheCardBuildsAroundAValue(_RenderEverywhere, SimpleTestCase):

    def test_html_override_is_markup_and_its_value_is_escaped(self):
        for key, html in self.render_everywhere(
                lambda card: card.add_entry(value=PAYLOAD, label='N', html_override='<div class="override">%1%</div>')).items():
            with self.subTest(pack=key[0], template=key[1]):
                page = _Page(html)
                self.assertEqual(len(page.find('div', **{'class': 'override'})), 1, html)
                self.assertEqual(page.find('img'), [], html)
                self.assertIn(f'<div class="override">{ESCAPED_PAYLOAD}</div>', html)

    def test_html_override_keeps_a_safe_value_as_markup(self):
        for key, html in self.render_everywhere(
                lambda card: card.add_entry(value=mark_safe('<b>bold</b>'), label='N',
                                            html_override='<div class="override">%1%</div>')).items():
            with self.subTest(pack=key[0], template=key[1]):
                self.assertIn('<div class="override"><b>bold</b></div>', html)

    def test_html_override_escapes_each_line_of_a_list(self):
        for key, html in self.render_everywhere(
                lambda card: card.add_entry(value=[PAYLOAD, 'two'], label='N', html_override='<i>%1%</i>')).items():
            with self.subTest(pack=key[0], template=key[1]):
                self.assertIn(f'<i>{ESCAPED_PAYLOAD}</i>', html)
                self.assertIn('<i>two</i>', html)
                self.assertEqual(_Page(html).find('img'), [], html)

    def test_a_merged_row_escapes_its_parts_and_keeps_its_separator(self):
        for key, html in self.render_everywhere(
                lambda card: card.add_entry(value=[PAYLOAD, mark_safe('<b>2</b>')], label='N',
                                            merge=True, merge_string=' &times; ')).items():
            with self.subTest(pack=key[0], template=key[1]):
                self.assertIn(f'{ESCAPED_PAYLOAD} &times; <b>2</b>', html)

    def test_a_row_style_escapes_what_fills_it(self):
        def build(card):
            card.add_row_style('styled', html='<div class="styled"><em>{label}</em>{value}<span>{extra}</span></div>')
            card.add_entry(value=PAYLOAD, label=PAYLOAD, extra=PAYLOAD, row_style='styled')

        for key, html in self.render_everywhere(build).items():
            with self.subTest(pack=key[0], template=key[1]):
                page = _Page(html)
                self.assertEqual(len(page.find('div', **{'class': 'styled'})), 1, html)
                self.assertEqual(page.find('img'), [], html)
                self.assertEqual(html.count(ESCAPED_PAYLOAD), 3, html)

    def test_a_row_style_escapes_what_is_looked_up_on_a_value(self):
        def build(card):
            card.add_row_style('styled', html='<p class="a">{value[v1]}</p><p class="b">{value[v2]}</p>')
            card.add_entry(value={'v1': PAYLOAD, 'v2': mark_safe('<b class="made">ok</b>')}, row_style='styled')

        for key, html in self.render_everywhere(build).items():
            with self.subTest(pack=key[0], template=key[1]):
                page = _Page(html)
                self.assertEqual(page.find('img'), [], html)
                self.assertIn(f'<p class="a">{ESCAPED_PAYLOAD}</p>', html)
                self.assertEqual(len(page.find('b', **{'class': 'made'})), 1, html)

    def test_a_row_style_keeps_an_element_value_as_markup(self):
        # A value built with html_classes (HtmlDiv and friends) is an object whose __str__ is
        # safe markup, handed to {value} whole -- a match list builds its rows that way.
        class Element:
            def __str__(self):
                return mark_safe('<span class="element">made</span>')

        def build(card):
            card.add_row_style('styled', html='<div class="styled">{value}</div>')
            card.add_entry(value=Element(), row_style='styled')

        for key, html in self.render_everywhere(build).items():
            with self.subTest(pack=key[0], template=key[1]):
                self.assertEqual(len(_Page(html).find('span', **{'class': 'element'})), 1, html)

    def test_a_row_style_looks_up_no_private_attribute(self):
        # The style is a format string, so text written into it -- a caller's mistake, but one
        # that happens -- gets the format mini-language, and {label.__init__.__globals__} would
        # walk from a value to module globals. A public attribute is still looked up, escaped.
        def build(card):
            card.add_row_style('styled', html='<p class="a">{label.__init__.__globals__}</p>'
                                              '<p class="b">{value._meta}</p><p class="c">{value.name}</p>')
            card.add_entry(value=Company(name='Brass & Co'), label='L', row_style='styled')

        for key, html in self.render_everywhere(build).items():
            with self.subTest(pack=key[0], template=key[1]):
                self.assertIn('<p class="a"></p><p class="b"></p><p class="c">Brass &amp; Co</p>', html)

    def test_a_row_style_placeholder_nothing_fills_reads_as_empty(self):
        def build(card):
            card.add_row_style('styled', html='<p class="menu">{menu}</p><p class="value">{value}</p>')
            card.add_entry(value='Row', row_style='styled')

        for key, html in self.render_everywhere(build).items():
            with self.subTest(pack=key[0], template=key[1]):
                self.assertIn('<p class="menu"></p><p class="value">Row</p>', html)

    def test_a_row_style_keeps_a_rendered_menu(self):
        def build(card):
            card.add_row_style('styled', html='<div class="styled">{value}{menu}</div>')
            card.add_entry(value='Row', row_style='styled',
                           menu=[HtmlMenuItem(html='<button class="made">Go</button>')])

        for key, html in self.render_everywhere(build).items():
            with self.subTest(pack=key[0], template=key[1]):
                self.assertEqual(len(_Page(html).find('button', **{'class': 'made'})), 1, html)

    def test_a_row_style_applies_a_format_spec_to_the_text(self):
        def build(card):
            card.add_row_style('styled', html='<pre>[{value:>6}]</pre>')
            card.add_entry(value='a<b', row_style='styled')

        for key, html in self.render_everywhere(build).items():
            with self.subTest(pack=key[0], template=key[1]):
                self.assertIn('<pre>[   a&lt;b]</pre>', html)

    def test_a_boolean_row_draws_its_icons(self):
        def build(card):
            card.add_entry(value=True, label='Yes')
            card.add_entry(value=False, label='No')

        for key, html in self.render_everywhere(build).items():
            with self.subTest(pack=key[0], template=key[1]):
                page = _Page(html)
                self.assertEqual(len(page.find('i', **{'class': 'fas fa-check'})), 1, html)
                self.assertEqual(len(page.find('i', **{'class': 'fas fa-times'})), 1, html)

    def test_a_sparkline_is_drawn(self):
        def build(card):
            card.add_entry(value=[1, 5, 3], label='Line', sparkline=True)
            card.add_entry(value=[1, 5, 3], label='Bars', sparkline='bar')

        for key, html in self.render_everywhere(build).items():
            with self.subTest(pack=key[0], template=key[1]):
                page = _Page(html)
                self.assertEqual(len(page.find('svg')), 2, html)
                self.assertEqual(len(page.find('polyline')), 1, html)
                self.assertEqual(len(page.find('rect')), 3, html)

    def test_auto_link_links_the_text_and_escapes_the_rest(self):
        value = f'see https://example.com/?a=1&b=2 or mail a@example.com {PAYLOAD}'
        for key, html in self.render_everywhere(
                lambda card: card.add_entry(value=value, label='N', auto_link=True)).items():
            with self.subTest(pack=key[0], template=key[1]):
                page = _Page(html)
                hrefs = [a['href'] for a in page.find('a')]
                self.assertIn('https://example.com/?a=1&b=2', hrefs)
                self.assertIn('mailto:a@example.com', hrefs)
                self.assertEqual(page.find('img'), [], html)

    def test_a_list_in_a_table_card_prints_no_stray_markup(self):
        # The table template's list branch used to print `">` in front of every line, the
        # remains of a tag that lost its start.
        view = _CardView()
        view.request = RequestFactory().get('/')
        for pack in PACKS:
            with self.subTest(pack=pack), override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                card = view.add_card('demo', title='Demo', template_name='table')
                card.add_entry(value=['one', 'two'], label='Lines')
                text = ''.join(_Page(card.render()).text)
                self.assertNotIn('">', text)
                self.assertIn('one', text)


class TestManyToManyBadges(_RenderEverywhere, TestCase):

    def test_each_badge_is_escaped(self):
        company = Company.objects.create(name='Company')
        company.sectors.add(Sector.objects.create(name=PAYLOAD), Sector.objects.create(name='Timber & Board'))
        for key, html in self.render_everywhere(lambda card: card.add_rows('sectors'), details_object=company).items():
            with self.subTest(pack=key[0], template=key[1]):
                page = _Page(html)
                self.assertEqual(page.find('img'), [], html)
                self.assertIn(ESCAPED_PAYLOAD, html)
                self.assertIn('Timber &amp; Board', html)
                self.assertEqual(len([s for s in page.find('span') if 'badge' in s.get('class', '')]), 2, html)

    def test_no_badges_reads_as_the_default(self):
        company = Company.objects.create(name='Company')
        for key, html in self.render_everywhere(lambda card: card.add_rows('sectors'), details_object=company).items():
            with self.subTest(pack=key[0], template=key[1]):
                self.assertIn('N/A', html)


class _ListView(CardList):
    model = Company


class TestCardListEntryNames(TestCase):
    """The left-hand list of a CardList page names each entry, and used to mark every name safe."""

    def render_list(self):
        pages = {}
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                view = _ListView()
                view.request = RequestFactory().get('/')
                view.display_list_entries()
                pages[pack] = view.add_list_card(list_entries=view.list_entries, card_name='list').render()
        return pages

    def test_a_name_is_escaped(self):
        Company.objects.create(name=PAYLOAD)
        for pack, html in self.render_list().items():
            with self.subTest(pack=pack):
                self.assertEqual(_Page(html).find('img'), [], html)
                self.assertIn(ESCAPED_PAYLOAD, html)

    def test_a_name_marked_safe_is_markup(self):
        class SafeNames(_ListView):
            def get_list_entry_name(self, entry_object):
                return format_html('<b class="made">{}</b>', entry_object.name)

        Company.objects.create(name='Brass & Co')
        view = SafeNames()
        view.request = RequestFactory().get('/')
        view.display_list_entries()
        html = view.add_list_card(list_entries=view.list_entries, card_name='list').render()
        self.assertEqual(len(_Page(html).find('b', **{'class': 'made'})), 1, html)
        self.assertIn('Brass &amp; Co', html)

    def test_a_name_handed_over_as_an_uncalled_method_is_called(self):
        # It used to work by accident -- mark_safe wraps a callable and the template called it --
        # and escaping it as it stands would print "<bound method ...>".
        class MethodNames(_ListView):
            def get_list_entry_name(self, entry_object):
                return entry_object.__str__

        Company.objects.create(name='Brass & Co')
        view = MethodNames()
        view.request = RequestFactory().get('/')
        view.display_list_entries()
        html = view.add_list_card(list_entries=view.list_entries, card_name='list').render()
        self.assertIn('Brass &amp; Co', html)
        self.assertNotIn('bound method', html)


class TestEscapeValue(SimpleTestCase):
    """escape_value is {{ value }}: str() first, then escaped unless marked safe."""

    def test_text_is_escaped(self):
        self.assertEqual(escape_value('<b>'), '&lt;b&gt;')

    def test_safe_markup_is_kept(self):
        self.assertEqual(escape_value(mark_safe('<b>')), '<b>')

    def test_the_result_is_marked_safe(self):
        self.assertIsInstance(escape_value('<b>'), SafeString)

    def test_other_values_are_strd_first(self):
        self.assertEqual(escape_value(None), 'None')
        self.assertEqual(escape_value(3), '3')
        self.assertEqual(escape_value(lazy(lambda: '<i>', str)()), '&lt;i&gt;')

    def test_an_object_whose_str_is_safe_markup_is_kept(self):
        class Element:
            def __str__(self):
                return mark_safe('<b>')

        self.assertEqual(escape_value(Element()), '<b>')
