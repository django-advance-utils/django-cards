"""``add_card(sub_tab_menu=...)``: a second, quieter row of tabs under a card's tab bar.

A group of pages under a top tab -- Summary, Items, Money, and under Summary its own Summary and
Settings -- wants a second row. A card has one ``tab_menu``, which every card template prints, so
the second row rides on it: ``TabMenuWithSubRow`` renders the top menu and then the sub menu in a
``django-card__sub-tabs`` row, styled in ``cards.css``. A sub row of one tab repeats the tab it sits
under, so it is left out, and so is one of none. That is counted as the row renders, the way
django-menus decides which tabs to draw: a tab hidden by ``visible`` or a view's permissions does
not count, and one added after the card was built does.
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
                html = card.render()
                self.assertEqual(_sub_rows(html), [], html)
                self.assertEqual(len(_Page(html).find('b', **{'class': 'top-tab'})), 3, html)

    def test_a_tab_the_user_may_not_see_does_not_count(self):
        """Counted as django-menus draws: by test_visible, which applies a view's permissions."""
        class Forbidden(HtmlMenuItem):
            def test_visible(self, request):
                self.visible = False
                return False

        sub = _tabs('Overview') + [Forbidden('<b class="sub-tab">Settings</b>')]
        html = _view().add_card('probe', title='Probe', tab_menu=_tabs(*TOP), sub_tab_menu=sub).render()
        self.assertEqual(_sub_rows(html), [], html)

    def test_no_top_tab_draws_no_second_row(self):
        for top in ([], _tabs(*TOP, visible=False)):
            with self.subTest(top=top):
                html = _view().add_card('probe', title='Probe', tab_menu=top, sub_tab_menu=_tabs(*SUB)).render()
                self.assertEqual(_sub_rows(html), [], html)

    def test_tabs_added_after_the_card_is_built_count(self):
        card = _view().add_card('probe', title='Probe', tab_menu=_tabs(*TOP), sub_tab_menu=_tabs('Overview'))
        self.assertEqual(_sub_rows(card.render()), [])
        card.tab_menu.sub_menu.add_items(*_tabs('Settings', cls='sub-tab'))
        self.assertEqual(len(_sub_rows(card.render())), 1)

    def test_a_tab_visible_by_a_callable_counts(self):
        sub = _tabs('Overview') + _tabs('Settings', visible=lambda request: True)
        card = _view().add_card('probe', title='Probe', tab_menu=_tabs(*TOP), sub_tab_menu=sub)
        self.assertEqual(len(_sub_rows(card.render())), 1)

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

    def test_a_setting_reaches_both_rows(self):
        """So the two rows match the url the same way."""
        top, sub, wrapped = self.wrapped()
        wrapped.compare_full_path = True
        self.assertTrue(top.compare_full_path)
        self.assertTrue(sub.compare_full_path)
        self.assertTrue(wrapped.compare_full_path)
        del wrapped.compare_full_path
        self.assertFalse(hasattr(top, 'compare_full_path'))
        self.assertFalse(hasattr(sub, 'compare_full_path'))

    def test_the_sub_menu_can_be_read_and_replaced(self):
        top, sub, wrapped = self.wrapped()
        self.assertIs(wrapped.sub_menu, sub)
        other = self._Menu('<ul>other</ul>')
        wrapped.sub_menu = other
        self.assertIs(wrapped.sub_menu, other)
        self.assertFalse(hasattr(top, 'sub_menu'))

    def test_it_can_be_copied(self):
        _top, _sub, wrapped = self.wrapped()
        for clone in (copy.copy(wrapped), copy.deepcopy(wrapped)):
            self.assertIs(type(clone.sub_menu), self._Menu)
            self.assertIn('<ul>top</ul>', clone.render())
