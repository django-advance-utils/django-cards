"""Three options JMS Cloud carried as its own CSS, now cards' own.

* **A treegrid in a panel region fills the region's width.** The table's 600px floor (still the
  default elsewhere) let a region be dragged narrower than the grid, which then scrolled
  sideways with its last column -- the one with the row's button -- under the splitter. A
  treegrid in a region or tab with no ``treegrid_min_width`` of its own now takes 100%.
* **``treegrid_hover='row'``** lights the whole row, for a grid read a row at a time; the default
  ``'cell'`` lights the cell, the cue for a grid edited in place. An editable cell in a row-hover
  grid keeps the cell cue too.
* **``add_panel_layout(scroll_cards=True)``**: every region card fills its region and scrolls its
  own body, so a card longer than the window keeps its header and tab bar in view.
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
        self.assertEqual(_table(html, 'blank')['style'], 'min-width:100%')
        self.assertEqual(_table(html, 'side')['style'], 'min-width:100%')
        self.assertEqual(_table(html, 'tabbed')['style'], 'min-width:100%')
        self.assertEqual(_table(html, 'given')['style'], 'min-width:900px')


class TestRowHover(SimpleTestCase):

    def test_cell_by_default_row_when_asked(self):
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                with self.subTest(pack=pack):
                    view = _view()
                    self.assertNotIn('treegrid--row-hover', _table(_grid(view).render())['class'])
                    rows = _grid(view, name='rows', treegrid_hover='row')
                    self.assertIn('treegrid--row-hover', _table(rows.render(), 'rows')['class'].split())

    def test_anything_else_is_refused(self):
        with self.assertRaisesMessage(ValueError, "'cell' or 'row'"):
            _grid(_view(), treegrid_hover='column')

    def test_the_row_lights_and_an_editable_cell_keeps_its_cue(self):
        css = (CSS / 'templates/cards/standard/_treegrid_css.html').read_text()
        self.assertIn('.fancytree-ext-table.treegrid--row-hover tbody tr:hover > td {', css)
        self.assertIn('.fancytree-ext-table.treegrid--row-hover tbody tr:hover > td.treegrid-editable:hover {', css)
        # every editable cell is marked, whether or not its column draws the pencil
        script = (CSS / 'templates/cards/standard/_treegrid_script.html').read_text()
        self.assertIn("$td.toggleClass('treegrid-editable', !!(!READ_ONLY && editInfo && !disabled));", script)


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

    def test_a_lone_region_card_fills_its_region_and_scrolls_its_body_but_not_a_grids(self):
        css = (CSS / 'static/cards/panel_layout/css/panel_layout.css').read_text()
        # :only-child -- several cards in a region keep the region's scroll, not an even split
        card = css[css.index('.panel-layout--scroll-cards .panel-region__content > .card:only-child {'):]
        self.assertIn('flex: 1;', card[:card.index('}')])
        # a treegrid card scrolls its own grid: its body is left alone
        body = css[css.index('.panel-layout--scroll-cards .panel-region__content > .card:only-child > '
                             '.card-body:not(:has(.fancytree-ext-table)) {'):]
        self.assertIn('overflow: auto;', body[:body.index('}')])

    def test_css_class_none_draws_no_stray_class(self):
        view = _view()
        layout = view.add_panel_layout(card_name='bare', css_class=None, persist=False, scroll_cards=True)
        layout.root.add_region('main', size='1fr')
        container = _Page(str(layout.render().render())).find('div', id='panel_layout_bare')[0]
        self.assertEqual(container['class'].split(), ['panel-layout', 'panel-layout--scroll-cards'])
