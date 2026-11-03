"""Three options JMS Cloud carried as its own CSS, now cards' own.

* **A treegrid in a panel region fills the region's width.** The table's 600px floor (still the
  default elsewhere) let a region be dragged narrower than the grid, which then scrolled
  sideways with its last column -- the one with the row's button -- under the splitter. A
  treegrid in a region or tab with no ``treegrid_min_width`` of its own now takes 100%.
* **``treegrid_hover='row'``** lights the whole row, for a grid read a row at a time; the default
  ``'cell'`` lights the cell, the cue for a grid edited in place. An editable cell in a row-hover
  grid keeps the cell cue too.
* **``add_panel_layout(scroll_cards=True)``**: the lone card of a region or tab fills it and
  scrolls its own body, so a card longer than the window keeps its header and tab bar in view.
"""
import pathlib

from django.test import RequestFactory, SimpleTestCase, override_settings
from django.views.generic import TemplateView

from cards.standard import CardMixin
from cards_examples.tests import SIMPLE_COLUMNS, simple_nodes
from cards_examples.tests.test_escaping import PACKS, _Page

CSS = pathlib.Path(__file__).resolve().parents[3] / 'cards'


class _View(CardMixin, TemplateView):
    pass


def _view():
    view = _View()
    view.request = RequestFactory().get('/')
    return view


def _grid(view, name='grid', **kwargs):
    return view.add_treegrid_card(card_name=name, title='Grid', treegrid_columns=SIMPLE_COLUMNS,
                                  treegrid_static_data=simple_nodes(name), **kwargs)


def _table(html, name='grid'):
    tables = _Page(html).find('table', id=f'{name}_table')
    assert len(tables) == 1, html
    return tables[0]


class TestATreegridsWidth(SimpleTestCase):

    def test_600px_unless_given_outside_a_layout(self):
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                with self.subTest(pack=pack):
                    view = _view()
                    self.assertEqual(_table(_grid(view).render())['style'], 'min-width:600px')
                    given = _grid(view, name='given', treegrid_min_width='800px')
                    self.assertEqual(_table(given.render(), 'given')['style'], 'min-width:800px')

    def test_100_percent_in_a_region_or_tab_unless_given(self):
        view = _view()
        layout = view.add_panel_layout(card_name='shell', persist=False)
        layout.root.add_region('side', size='300px').add_card(_grid(view, name='side'))
        tab = layout.root.add_region('main', size='1fr').add_tab('one', title='One')
        tab.add_card(_grid(view, name='tabbed'))
        tab.add_card(_grid(view, name='given', treegrid_min_width='900px'))
        tab.add_card(_grid(view, name='blank', treegrid_min_width=''))
        html = str(layout.render().render())
        self.assertEqual(_table(html, 'blank')['style'], 'min-width:')  # '' is no floor, as before
        self.assertEqual(_table(html, 'side')['style'], 'min-width:100%')
        self.assertEqual(_table(html, 'tabbed')['style'], 'min-width:100%')
        self.assertEqual(_table(html, 'given')['style'], 'min-width:900px')


class TestAReloadKeepsTheRegionWidth(SimpleTestCase):

    def test_the_width_is_set_as_the_grid_is_placed(self):
        """An ajax reload draws the card alone (_render_template), not the layout around it."""
        view = _view()
        grid = _grid(view)
        view.add_panel_layout(card_name='shell', persist=False).root.add_region('side', size='300px').add_card(grid)
        self.assertEqual(_table(grid._render_template())['style'], 'min-width:100%')


class TestRowHover(SimpleTestCase):

    def test_cell_by_default_row_when_asked(self):
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                with self.subTest(pack=pack):
                    view = _view()
                    self.assertNotIn('treegrid--row-hover', _table(_grid(view).render())['class'])
                    rows = _grid(view, name='rows', treegrid_hover='row')
                    self.assertIn('treegrid--row-hover', _table(rows.render(), 'rows')['class'].split())

    def test_none_is_the_default(self):
        self.assertNotIn('treegrid--row-hover', _table(_grid(_view(), treegrid_hover=None).render())['class'])

    def test_anything_else_is_refused(self):
        with self.assertRaisesMessage(ValueError, "'cell' or 'row'"):
            _grid(_view(), treegrid_hover='column')

    def test_the_row_lights_and_an_editable_cell_keeps_its_cue(self):
        css = (CSS / 'templates/cards/standard/_treegrid_css.html').read_text()
        # an overlay, so a cell's own class colour survives; the plain cell cue is for 'cell' grids
        row = css[css.index('.fancytree-ext-table.treegrid--row-hover tbody tr:hover > td {'):]
        self.assertIn('background-image: linear-gradient(', row[:row.index('}')])
        self.assertNotIn('background-color', row[:row.index('}')])
        # the default cell rule is left as it was, so a project's own overrides still win
        self.assertIn('    .fancytree-ext-table tbody td:hover {', css)
        self.assertNotIn(':not(.treegrid--row-hover)', css)
        self.assertIn('.fancytree-ext-table.treegrid--row-hover tbody tr:hover > td.treegrid-editable:hover {', css)
        # every editable cell is marked, whether or not its column draws the pencil
        script = (CSS / 'templates/cards/standard/_treegrid_script.html').read_text()
        self.assertIn("$td.toggleClass('treegrid-editable', !!(!READ_ONLY && editInfo && !disabled));", script)
        self.assertIn("$nodeTd.toggleClass('treegrid-editable', titleEditable);", script)


class TestScrollCards(SimpleTestCase):

    def test_off_by_default_and_a_class_when_asked(self):
        view = _view()
        plain = view.add_panel_layout(card_name='plain', persist=False)
        plain.root.add_region('main', size='1fr')
        self.assertNotIn('panel-layout--scroll-cards', str(plain.render().render()))
        scrolling = view.add_panel_layout(card_name='scrolling', css_class='mine', persist=False, scroll_cards=True)
        scrolling.root.add_region('main', size='1fr')
        container = _Page(str(scrolling.render().render())).find('div', id='panel_layout_scrolling')[0]
        self.assertEqual(container['class'].split(), ['panel-layout', 'mine', 'panel-layout--scroll-cards'])

    def test_a_region_or_tab_holding_one_card_is_marked(self):
        view = _view()
        layout = view.add_panel_layout(card_name='shell', persist=False, scroll_cards=True)
        lone = view.add_card('lone', title='Lone', searchable=True, ajax_reload=True)
        lone.add_entry(value='x', label='X')
        layout.root.add_region('lone', size='1fr').add_card(lone)
        pair = layout.root.add_region('pair', size='1fr')
        pair.add_card(view.add_card('a', title='A'))
        pair.add_card(view.add_card('b', title='B'))
        layout.root.add_region('tabs', size='1fr').add_tab('t', title='T').add_card(view.add_card('c', title='C'))
        page = _Page(str(layout.render().render()))
        marked = [a for a in page.find('div') if 'panel-region__content--single' in (a.get('class') or '').split()]
        self.assertEqual(len(marked), 2)  # the lone region and the tab -- not the pair
        self.assertIn('tab-pane', marked[1]['class'])

    def test_a_treegrid_or_a_slot_alone_is_not_marked(self):
        view = _view()
        layout = view.add_panel_layout(card_name='shell', persist=False, scroll_cards=True)
        layout.root.add_region('grid', size='1fr').add_card(_grid(view))
        layout.root.add_region('slot', size='1fr').add_slot()
        page = _Page(str(layout.render().render()))
        self.assertEqual([a for a in page.find('div') if 'panel-region__content--single' in (a.get('class') or '').split()], [])

    def test_the_lone_card_fills_and_scrolls_in_a_region_a_tab_and_a_reload_wrapper(self):
        css = (CSS / 'static/cards/panel_layout/css/panel_layout.css').read_text()
        scroll = css[css.index('add_panel_layout(scroll_cards=True)'):]
        # only a tab pane is made a flex column (out-ranking the active pane's display: block); a
        # region's display is never set, so a collapsed region's display: none stands
        self.assertIn('.panel-region__content.tab-content > .tab-pane.active.panel-region__content--single {', scroll)
        self.assertNotIn('.panel-layout--scroll-cards .panel-region__content--single {', scroll)
        self.assertNotIn('.panel-layout--scroll-cards .panel-region__content--single,', scroll)
        card = css[css.index('.panel-layout--scroll-cards .panel-region__content--single > .card,'):]
        self.assertIn('> .django-card__ajax > .card', card[:card.index('{')])
        body = css[css.index('.panel-layout--scroll-cards .panel-region__content--single > .card > .card-body,'):]
        self.assertIn('overflow: auto;', body[:body.index('}')])
        self.assertNotIn(':has(', css[css.index('add_panel_layout(scroll_cards=True)'):])
        reloads = _view().add_card('r', title='R', ajax_reload=True)
        self.assertIn('id="r_ajax" class="django-card__ajax"', reloads.render())

    def test_self_sizing_and_collapsible_cards_are_not_marked_and_nothing_is_without_scroll_cards(self):
        view = _view()
        self.assertFalse(view.add_accordion_card(card_name='acc', title='Acc', panels=[]).fills_region)
        self.assertFalse(view.add_card('folds', title='Folds', collapsed=False).fills_region)
        self.assertFalse(view.add_layout_card('rows').fills_region)
        self.assertFalse(view.add_card('picks', title='Picks', template_name='list_selection').fills_region)
        self.assertFalse(_grid(view, name='tree').fills_region)
        for name in ('plain', 'table', 'html', 'message'):
            with self.subTest(template=name):
                template = None if name == 'plain' else name
                self.assertTrue(view.add_card(f'fill_{name}', title='Fill', template_name=template).fills_region)
        layout = view.add_panel_layout(card_name='inner', persist=False)  # no scroll_cards
        layout.root.add_region('main', size='1fr').add_card(view.add_card('alone', title='Alone'))
        self.assertNotIn('panel-region__content--single', str(layout.render().render()))

    def test_css_class_none_draws_no_stray_class(self):
        view = _view()
        layout = view.add_panel_layout(card_name='bare', css_class=None, persist=False, scroll_cards=True)
        layout.root.add_region('main', size='1fr')
        container = _Page(str(layout.render().render())).find('div', id='panel_layout_bare')[0]
        self.assertEqual(container['class'].split(), ['panel-layout', 'panel-layout--scroll-cards'])
