"""``add_rail_card``: a column of icons down a card's left side, the open panel beside it.

Each icon opens its panel, one at a time. A panel holding ``panels`` of its own opens a second
column of icons beside the first, and that column's icons open panes or further columns. The panel
list takes the accordion's keys, so a page can swap ``add_accordion_card`` for ``add_rail_card``.

It is a card, so it goes wherever a card goes -- a panel region or tab, an accordion panel. The
server decides what shows first (each column's ``expanded`` panel, or its first); the shared script,
emitted once per request, shows what the active buttons lead to after a click.
"""
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView

from cards import render_scope
from cards.standard import CardMixin
from cards_examples.tests.test_escaping import PACKS, _Page


class _View(CardMixin, TemplateView):
    pass


def _view():
    view = _View()
    view.request = RequestFactory().get('/')
    return view


def _body(view, name, text):
    card = view.add_card(name, title=name.title())
    card.add_entry(value=text, label='Text')
    return card


def _rail(view, card_name='tools', **kwargs):
    panels = kwargs.pop('panels', None)
    if panels is None:
        panels = [
            {'title': 'Sizes', 'icon': 'fas fa-ruler-combined', 'card': _body(view, 'sizes', 'sizes text')},
            {'title': 'Drawings', 'icon': 'fas fa-cut', 'panels': [
                {'title': 'Sections', 'icon': 'fas fa-cut', 'card': _body(view, 'sections', 'sections text')},
                {'title': 'Elevations', 'icon': 'fas fa-drafting-compass', 'expanded': True,
                 'card': _body(view, 'elevations', 'elevations text')},
            ]},
            {'title': 'Notes', 'card': _body(view, 'notes', 'notes text')},
        ]
    return view.add_rail_card(card_name=card_name, panels=panels, **kwargs)


def _columns(page):
    return [a for a in page.find('div') if 'django-card-rail__column' in (a.get('class') or '').split()]


def _panes(page):
    return [a for a in page.find('div') if 'django-card-rail__pane' in (a.get('class') or '').split()]


def _buttons(page):
    return [a for a in page.find('button') if 'django-card-rail__btn' in (a.get('class') or '').split()]


class TestTheRail(SimpleTestCase):

    def test_a_column_of_icons_and_the_first_panel_open(self):
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack), self.subTest(pack=pack):
                page = _Page(_rail(_view()).render())
                first, nested = _columns(page)
                self.assertNotIn('hidden', first)
                self.assertIn('hidden', nested)  # Drawings is not the open panel
                buttons = {b['title']: b for b in _buttons(page)}
                self.assertEqual(list(buttons), ['Sizes', 'Drawings', 'Notes', 'Sections', 'Elevations'])
                self.assertIn('active', buttons['Sizes']['class'].split())
                self.assertEqual(buttons['Sizes']['aria-label'], 'Sizes')
                self.assertEqual(buttons['Sizes']['aria-selected'], 'true')
                self.assertEqual([p['id'] for p in _panes(page) if 'hidden' not in p], [buttons['Sizes']['aria-controls']])

    def test_a_panel_with_panels_opens_a_column_not_a_pane(self):
        page = _Page(_rail(_view()).render())
        drawings = [b for b in _buttons(page) if b['title'] == 'Drawings'][0]
        self.assertIn('django-card-rail__btn--group', drawings['class'].split())
        self.assertEqual(drawings['aria-expanded'], 'false')
        nested = _columns(page)[1]
        self.assertEqual(drawings['data-rail-column'], nested['id'])
        self.assertEqual(nested['data-rail-parent'], drawings['id'])
        self.assertNotIn('data-rail-pane', drawings)

    def test_expanded_down_a_branch_opens_its_column_and_pane(self):
        view = _view()
        page = _Page(_rail(view, panels=[
            {'title': 'Sizes', 'card': _body(view, 'sizes', 'x')},
            {'title': 'Drawings', 'expanded': True, 'panels': [
                {'title': 'Sections', 'card': _body(view, 'sections', 'x')},
                {'title': 'Elevations', 'expanded': True, 'card': _body(view, 'elevations', 'x')},
            ]},
        ]).render())
        self.assertTrue(all('hidden' not in c for c in _columns(page)))
        drawings = [b for b in _buttons(page) if b['title'] == 'Drawings'][0]
        self.assertEqual(drawings['aria-expanded'], 'true')
        elevations = [b for b in _buttons(page) if b['title'] == 'Elevations'][0]
        self.assertEqual([p['id'] for p in _panes(page) if 'hidden' not in p], [elevations['aria-controls']])

    def test_a_closed_column_keeps_its_own_open_panel(self):
        """Elevations is marked expanded in a column not on show: that column opens on it."""
        page = _Page(_rail(_view()).render())
        nested = _buttons(page)[3:]
        self.assertEqual([b['aria-selected'] for b in nested], ['false', 'true'])

    def test_columns_nest_deeper(self):
        view = _view()
        page = _Page(_rail(view, panels=[{'title': 'A', 'panels': [{'title': 'B', 'panels': [
            {'title': 'C', 'card': _body(view, 'deep', 'deep text')}]}]}]).render())
        self.assertEqual(len(_columns(page)), 3)
        self.assertTrue(all('hidden' not in c for c in _columns(page)))
        self.assertIn('deep text', ''.join(page.text))

    def test_ids_are_unique_however_the_panels_are_named(self):
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack), self.subTest(pack=pack):
                view = _view()
                same = [{'title': 'Same', 'card': _body(view, 'one', 'x')},
                        {'title': 'Same', 'panels': [{'title': 'Same', 'card': _body(view, 'two', 'x')},
                                                     {'title': 'Same', 'panels': [
                                                         {'title': 'Same', 'card': _body(view, 'three', 'x')}]}]}]
                html = _rail(view, card_name='a', panels=same).render() + _rail(view, card_name='b', panels=[
                    {'title': 'Same', 'card': _body(view, 'four', 'x')}]).render()
                ids = [a['id'] for _, a in _Page(html).elements if 'id' in a]
                self.assertEqual(len(ids), len(set(ids)), sorted(i for i in ids if ids.count(i) > 1))

    def test_every_control_names_a_column_or_pane_that_is_there(self):
        page = _Page(_rail(_view()).render())
        ids = {a['id'] for _, a in page.elements if 'id' in a}
        for button in _buttons(page):
            with self.subTest(button=button['title']):
                self.assertIn(button['aria-controls'], ids)
        for pane in _panes(page):
            self.assertIn(pane['aria-labelledby'], ids)

    def test_an_icon_less_panel_shows_its_first_letter(self):
        page = _Page(_rail(_view()).render())
        letters = [a for a in page.find('span') if a.get('class') == 'django-card-rail__letter']
        self.assertEqual(len(letters), 1)
        self.assertIn('N', page.text)
        view = _view()
        safe = _rail(view, panels=[{'title': mark_safe('<b>Bold</b>'), 'card': _body(view, 'a', 'x')}]).render()
        self.assertIn('aria-hidden="true">B</span>', safe)

    def test_titles_are_escaped_unless_marked_safe(self):
        view = _view()
        html = _rail(view, panels=[{'title': '<b>Bold</b> & co', 'card': _body(view, 'a', 'x')},
                                   {'title': mark_safe('<i class="mine">Mine</i>'), 'card': _body(view, 'b', 'x')}]).render()
        self.assertNotIn('<b>Bold</b>', html)
        self.assertIn('<span>&lt;b&gt;Bold&lt;/b&gt; &amp; co</span>', html)
        page = _Page(html)
        self.assertEqual(len(page.find('i', **{'class': 'mine'})), 1)  # the pane's title, as given
        # a tooltip is text: a title marked safe gives its words, not markup that would end the attribute
        self.assertEqual([b['title'] for b in _buttons(page)], ['Bold & co', 'Mine'])
        self.assertEqual([b['aria-label'] for b in _buttons(page)], ['Bold & co', 'Mine'])

    def test_the_pane_title_and_the_cards_own_header(self):
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack), self.subTest(pack=pack):
                titled = _rail(_view()).render()
                self.assertIn('django-card-rail__body--titled', titled)
                self.assertEqual(len([a for a in _Page(titled).find('div')
                                      if a.get('class') == 'django-card-rail__pane-title']), 4)
                bare = _Page(_rail(_view(), pane_titles=False).render())
                self.assertEqual([a for a in bare.find('div') if a.get('class') == 'django-card-rail__pane-title'], [])
                self.assertNotIn('django-card-rail__body--titled', bare.find('div', id='tools_body')[0]['class'])

    def test_a_header_only_with_a_title(self):
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack), self.subTest(pack=pack):
                view = _view()
                self.assertNotIn('<h5', _rail(view, panels=[]).render())
                self.assertIn('Tools', _rail(view, card_name='titled', title='Tools', panels=[]).render())

    def test_the_height_is_the_cards(self):
        self.assertIn('style="height: 100%;"', _rail(_view()).render())
        self.assertIn('style="height: 480px;"', _rail(_view(), height='480px').render())

    def test_no_panels_draws_an_empty_rail(self):
        page = _Page(_rail(_view(), panels=[]).render())
        self.assertEqual((_columns(page), _panes(page)), ([], []))

    def test_a_panel_with_a_card_and_panels_is_refused(self):
        view = _view()
        card = _body(view, 'both', 'x')
        with self.assertRaisesMessage(ValueError, "'Both' holds both panels and a card"):
            _rail(view, panels=[{'title': 'Both', 'card': card, 'panels': [{'title': 'X'}]}]).render()

    def test_panels_that_are_not_a_list_are_refused(self):
        with self.assertRaisesMessage(ValueError, 'a list of dicts'):
            _rail(_view(), panels=[{'title': 'A', 'panels': {'title': 'B'}}]).render()


class TestTheSharedScript(SimpleTestCase):

    def test_once_per_request_for_every_rail(self):
        with self.subTest('in a request'):
            render_scope._open_scope()
            try:
                view = _view()
                html = _rail(view, card_name='a').render() + _rail(view, card_name='b').render()
            finally:
                render_scope._close_scope()
            self.assertEqual(html.count('window.djangoCardsRail = window.djangoCardsRail ||'), 1)
            self.assertEqual(html.count('.django-card-rail__btn--group::after {'), 1)

    def test_it_listens_on_the_document_so_a_reloaded_rail_works(self):
        html = _rail(_view()).render()
        self.assertIn("document.addEventListener('click'", html)
        self.assertIn("'shown.cards.rail'", html)
        self.assertIn('columns.adjust()', html)


class TestWhereARailGoes(SimpleTestCase):

    def test_alone_in_a_scroll_cards_region_it_fills_it(self):
        view = _view()
        rail = _rail(view)
        self.assertTrue(rail.fills_region)
        layout = view.add_panel_layout(card_name='shell', persist=False, scroll_cards=True)
        layout.root.add_region('side', size='360px').add_card(rail)
        layout.root.add_region('main', size='1fr').add_card(view.add_card('main', title='Main'))
        page = _Page(str(layout.render().render()))
        marked = [a for a in page.find('div') if 'panel-region__content--single' in (a.get('class') or '').split()]
        self.assertEqual(len(marked), 2)
        self.assertEqual(len(_columns(page)), 2)

    def test_the_rail_keeps_its_own_class_where_a_region_sets_the_cards(self):
        """A region draws its cards with a card_css_class of its own: the rail's layout hangs off a
        class written into the template, not that one, or the columns stack one under another."""
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack), self.subTest(pack=pack):
                view = _view()
                layout = view.add_panel_layout(card_name='shell', persist=False)
                layout.root.add_region('side', size='360px').add_card(_rail(view))
                tab = layout.root.add_region('main', size='1fr').add_tab('t', title='T')
                tab.add_card(_rail(view, card_name='tabbed'))
                page = _Page(str(layout.render().render()))
                for card_id in ('tools_card', 'tabbed_card'):
                    self.assertIn('django-card-rail', page.find('div', id=card_id)[0]['class'].split())

    def test_in_an_accordion_panel(self):
        view = _view()
        rail = _rail(view, height='420px')
        html = view.add_accordion_card(card_name='side', panels=[{'title': 'Tools', 'card': rail}]).render()
        page = _Page(html)
        self.assertEqual(len(_columns(page)), 2)
        self.assertIn('sizes text', ''.join(page.text))

    def test_a_card_in_a_nested_column_cannot_also_be_a_section(self):
        view = _view()
        deep = _body(view, 'deep', 'x')
        _rail(view, panels=[{'title': 'A', 'panels': [{'title': 'B', 'card': deep}]}])
        with self.assertRaises(ValueError):
            view.add_card('stack', title='Stack').add_sections([deep])

    def test_a_section_card_cannot_go_in_a_nested_column(self):
        view = _view()
        stacked = _body(view, 'stacked', 'x')
        view.add_card('stack', title='Stack').add_sections([stacked])
        with self.assertRaisesMessage(ValueError, 'a rail panel'):
            _rail(view, panels=[{'title': 'A', 'panels': [{'title': 'B', 'card': stacked}]}]).render()
