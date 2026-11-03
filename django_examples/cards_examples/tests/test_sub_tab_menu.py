"""``add_card(sub_tab_menu=...)``: a second, quieter row of tabs under a card's tab bar.

A group of pages under a top tab -- Summary, Items, Money, and under Summary its own Summary and
Settings -- wants a second row. A card has one ``tab_menu``, which every card template prints, so
the second row rides on it: ``TabMenuWithSubRow`` renders the top menu and then the sub menu in a
``django-card__sub-tabs`` row, styled in ``cards.css``. A sub row of one tab repeats the tab it sits
under, so it is left out, and so is one of none; tabs switched off by ``visible`` do not count.
"""
import copy

from django.test import RequestFactory, SimpleTestCase, override_settings
from django.views.generic import TemplateView
from django_menus.menu import HtmlMenuItem

from cards.base import TabMenuWithSubRow
from cards.standard import CardMixin
from cards_examples.tests.test_escaping import PACKS, _Page


class _CardView(CardMixin, TemplateView):
    pass


def _view():
    view = _CardView()
    view.request = RequestFactory().get('/')
    return view


def _tabs(*names, cls='top-tab', **kwargs):
    return [HtmlMenuItem(f'<b class="{cls}">{name}</b>', **kwargs) for name in names]


TOP = ('Summary', 'Items', 'Money')
SUB = ('Overview', 'Settings')


def _sub_rows(html):
    return [a for a in _Page(html).find('div') if a.get('class') == 'django-card__sub-tabs']


def _cards(**kwargs):
    """The same card built as each kind of body: rows, a table, html, and empty (``message``)."""
    def default():
        card = _view().add_card('probe', title='Probe', **kwargs)
        card.add_entry(value='one', label='First')
        return card

    def table():
        card = _view().add_card('probe', title='Probe', template_name='table', **kwargs)
        card.add_entry(value='one', label='First')
        return card

    yield 'default', default
    yield 'table', table
    yield 'html', lambda: _view().add_html_data_card(card_name='probe', title='Probe', html='<p>x</p>', **kwargs)
    yield 'empty', lambda: _view().add_card('probe', title='Probe', is_empty=True, **kwargs)


class TestASubRow(SimpleTestCase):

    def test_two_or_more_tabs_draw_a_second_row_under_the_first(self):
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                for name, build in _cards(tab_menu=_tabs(*TOP), sub_tab_menu=_tabs(*SUB, cls='sub-tab')):
                    with self.subTest(pack=pack, card=name):
                        html = build().render()
                        page = _Page(html)
                        self.assertEqual(len(page.find('b', **{'class': 'top-tab'})), 3, html)
                        self.assertEqual(len(page.find('b', **{'class': 'sub-tab'})), 2, html)
                        self.assertEqual(len(_sub_rows(html)), 1, html)
                        # the top row first, the sub row under it
                        self.assertLess(html.index('top-tab'), html.index('django-card__sub-tabs'))
                        self.assertLess(html.index('django-card__sub-tabs'), html.index('sub-tab"'))

    def test_the_stylesheet_comes_with_it(self):
        card = _view().add_card('probe', title='Probe', tab_menu=_tabs(*TOP), sub_tab_menu=_tabs(*SUB))
        self.assertIn('cards/css/cards.css', card.render())

    def test_one_tab_or_none_draws_no_second_row(self):
        for sub in (_tabs('Overview'), [], _tabs('Overview', 'Settings', visible=False),
                    _tabs('Overview') + _tabs('Settings', visible=lambda request: False)):
            with self.subTest(sub=sub):
                card = _view().add_card('probe', title='Probe', tab_menu=_tabs(*TOP), sub_tab_menu=sub)
                self.assertNotIsInstance(card.tab_menu, TabMenuWithSubRow)
                html = card.render()
                self.assertEqual(_sub_rows(html), [], html)
                self.assertNotIn('cards/css/cards.css', html)

    def test_a_tab_visible_by_a_callable_counts(self):
        sub = _tabs('Overview') + _tabs('Settings', visible=lambda request: True)
        card = _view().add_card('probe', title='Probe', tab_menu=_tabs(*TOP), sub_tab_menu=sub)
        self.assertIsInstance(card.tab_menu, TabMenuWithSubRow)

    def test_a_sub_row_needs_a_tab_bar_to_sit_under(self):
        with self.assertRaises(ValueError):
            _view().add_card('probe', title='Probe', sub_tab_menu=_tabs(*SUB))

    def test_it_composes_with_a_scrollable_tab_bar(self):
        card = _view().add_card('probe', title='Probe', tab_menu=_tabs(*TOP), scrollable_tab_menu=True,
                                sub_tab_menu=_tabs(*SUB, cls='sub-tab'))
        html = card.render()
        self.assertIn('class="stm"', html)
        self.assertEqual(len(_sub_rows(html)), 1, html)
        # the scroller holds the top row only
        self.assertLess(html.index('stm__wrapper'), html.index('django-card__sub-tabs'))


class TestTabMenuWithSubRow(SimpleTestCase):
    """It stands in for the top menu: reads, writes and deletes go to it."""

    class _Menu:
        def __init__(self, html):
            self.html = html
            self.compare_full_path = False

        def render(self):
            return self.html

    def wrapped(self):
        top, sub = self._Menu('<ul>top</ul>'), self._Menu('<ul>sub</ul>')
        return top, sub, TabMenuWithSubRow(top, sub)

    def test_writes_reads_and_deletes_reach_the_top_menu(self):
        top, sub, wrapped = self.wrapped()
        wrapped.compare_full_path = True
        self.assertTrue(top.compare_full_path)
        self.assertFalse(sub.compare_full_path)
        self.assertTrue(wrapped.compare_full_path)
        del wrapped.compare_full_path
        self.assertFalse(hasattr(top, 'compare_full_path'))

    def test_the_sub_menu_is_reachable(self):
        _top, sub, wrapped = self.wrapped()
        self.assertIs(wrapped.sub_menu, sub)

    def test_it_can_be_copied(self):
        _top, _sub, wrapped = self.wrapped()
        for clone in (copy.copy(wrapped), copy.deepcopy(wrapped)):
            self.assertIn('<ul>sub</ul>', clone.render())
