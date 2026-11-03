"""Four guards around a card's chrome.

* **An empty card keeps its tab bar and header buttons.** ``is_empty=True`` routes a card to the
  ``message`` template; a tab with nothing in it still needs the tabs to leave it by, and the
  button that would fill it. Held here so the routing cannot drop them.
* **A panel layout's id may not be its card's.** The wrapper card takes ``card_name`` as its DOM
  id, and ``panel_layout.js`` finds the layout by id, taking the first element carrying it -- the
  wrapper -- so the layout never sized itself. Refused at construction.
* **A row's ``status_dot`` is a css colour or nothing.** It is written into ``style="background:
  ..."``, where escaping does not stop a semicolon adding declarations of its own.
* **A scrollable tab bar opens on its active tab, and is written through.** It forwarded reads to
  the menu it wraps but not writes, so a setting made on the wrapper never reached the menu.
"""
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.views.generic import TemplateView
from django_menus.menu import HtmlMenuItem

from cards.base import ScrollableTabMenu, css_colour
from cards.panel_layout import PanelLayout
from cards.standard import CardMixin
from cards_examples.tests.test_escaping import PACKS, ROW_TEMPLATES, _Page

STYLE_PAYLOAD = 'red;position:fixed;inset:0'


class _CardView(CardMixin, TemplateView):
    pass


def _view():
    view = _CardView()
    view.request = RequestFactory().get('/')
    return view


class TestAnEmptyCardKeepsItsChrome(SimpleTestCase):

    def test_the_tab_bar_and_header_buttons_survive(self):
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                with self.subTest(pack=pack):
                    card = _view().add_card(
                        'probe', title='Probe', is_empty=True, empty_message='Nothing yet',
                        menu=[HtmlMenuItem('<b class="probe-add">Add</b>')],
                        tab_menu=[HtmlMenuItem('<b class="probe-tab">One</b>'),
                                  HtmlMenuItem('<b class="probe-tab">Two</b>')])
                    page = _Page(card.render())
                    self.assertEqual(len(page.find('b', **{'class': 'probe-tab'})), 2)
                    self.assertEqual(len(page.find('b', **{'class': 'probe-add'})), 1)
                    self.assertIn('Nothing yet', ''.join(page.text))


class TestAPanelLayoutIdIsItsOwn(SimpleTestCase):

    def test_the_cards_name_is_refused(self):
        with self.assertRaisesMessage(ValueError, "'shell'"):
            PanelLayout(view=None, card_name='shell', layout_id='shell')

    def test_the_view_helper_refuses_it_too(self):
        with self.assertRaises(ValueError):
            _view().add_panel_layout(card_name='shell', layout_id='shell')

    def test_the_default_and_a_name_of_its_own_are_taken(self):
        self.assertEqual(PanelLayout(view=None, card_name='shell').layout_id, 'panel_layout_shell')
        self.assertEqual(PanelLayout(view=None, card_name='shell', layout_id='grid').layout_id, 'grid')

    def test_the_rendered_ids_differ(self):
        layout = _view().add_panel_layout(card_name='shell')
        layout.root.add_region('main', size='1fr')
        html = layout.render().render()
        self.assertEqual(len(_Page(html).find('div', id='shell')), 1, html)
        self.assertEqual(len(_Page(html).find('div', id='panel_layout_shell')), 1, html)


class TestCssColour(SimpleTestCase):

    def test_colours_are_kept(self):
        for colour in ('green', 'transparent', 'currentColor', '#fff', '#ffff', '#90EE90', '#90ee90cc',
                       'rgb(0, 128, 0)', 'rgb(0 128 0 / 50%)', 'rgba(0,0,0,.5)', 'hsl(120deg 100% 25%)',
                       'var(--ok)', 'var(--status_ok-2)'):
            with self.subTest(colour=colour):
                self.assertEqual(css_colour(colour), colour)

    def test_surrounding_space_is_ignored(self):
        self.assertEqual(css_colour(' green '), 'green')

    def test_anything_that_could_add_a_declaration_is_dropped(self):
        for colour in (STYLE_PAYLOAD, 'red;', 'red "x"', "red'", 'url(x)', 'rgb(0,0,0);top:0',
                       'rgb(0,0,0) url(x)', 'var(--a);top:0', 'var(a)', 'expression(alert(1))',
                       '#ggg', '#12345', '90EE90', '', 'red blue', 'rgb((0))', 'rgb(0,0,0\n)'):
            with self.subTest(colour=colour):
                self.assertIsNone(css_colour(colour))

    def test_none_is_none(self):
        self.assertIsNone(css_colour(None))


class TestAStatusDotIsChecked(SimpleTestCase):

    def render_everywhere(self, status_dot):
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                for template_name in ROW_TEMPLATES:
                    card = _view().add_card('probe', title='Probe', template_name=template_name)
                    card.add_entry(value='Up', label='Server', status_dot=status_dot)
                    yield pack, template_name, card.render()

    @staticmethod
    def dots(html):
        return [a for a in _Page(html).find('span') if 'border-radius:50%' in (a.get('style') or '')]

    def test_a_colour_draws_a_dot(self):
        for pack, template_name, html in self.render_everywhere('green'):
            with self.subTest(pack=pack, template=template_name):
                dots = self.dots(html)
                self.assertEqual(len(dots), 1, html)
                self.assertIn('background:green;', dots[0]['style'])

    def test_a_colour_that_is_not_one_draws_no_dot(self):
        for pack, template_name, html in self.render_everywhere(STYLE_PAYLOAD):
            with self.subTest(pack=pack, template=template_name):
                self.assertEqual(self.dots(html), [], html)
                self.assertNotIn('position:fixed', html)


class _Menu:
    """Stands in for an HtmlMenu: a tab bar with one tab marked active."""

    def __init__(self):
        self.compare_full_path = False

    def render(self):
        return ('<ul class="nav nav-tabs"><li class="nav-item"><a class="nav-link" href="#">One</a></li>'
                '<li class="nav-item"><a class="nav-link active" href="#">Two</a></li></ul>')


class TestAScrollableTabMenu(SimpleTestCase):

    def test_a_write_reaches_the_wrapped_menu(self):
        menu = _Menu()
        wrapped = ScrollableTabMenu(menu)
        wrapped.compare_full_path = True
        self.assertTrue(menu.compare_full_path)
        self.assertTrue(wrapped.compare_full_path)
        self.assertNotIn('compare_full_path', vars(wrapped))

    def test_a_read_still_falls_through(self):
        self.assertFalse(ScrollableTabMenu(_Menu()).compare_full_path)

    def test_its_script_scrolls_the_strip_to_the_active_tab(self):
        html = ScrollableTabMenu(_Menu()).render()
        self.assertIn(".nav-link.active,.active>.nav-link", html)
        self.assertIn('u.scrollLeft+=', html)
        # The strip alone moves: scrollIntoView would take the page and its scrollers along.
        self.assertNotIn('scrollIntoView', html)
