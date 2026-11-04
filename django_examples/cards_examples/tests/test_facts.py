"""``add_heading()`` and ``add_facts()``: the summary layout record pages keep building by hand.

* **add_heading(title, note=None)** starts a group of rows with a small-caps heading, and an aside
  at its end -- "65 logins in 90 days".
* **add_facts(*columns)** lays fact columns side by side, each a heading over a stack of
  label-over-value entries filled top to bottom, so columns can hold different numbers of facts.
  Each fact is an ordinary entry -- a field name or a dict of add_entry options -- drawn by the
  same markup as a row's (``_entry.html``), so a badge, a menu or a default work unchanged.
"""
import pathlib

from django.test import RequestFactory, SimpleTestCase, override_settings
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView
from django_menus.menu import HtmlMenuItem

from cards.standard import CardMixin
from cards_examples.models import Company
from cards_examples.tests.test_escaping import PACKS, ROW_TEMPLATES, _Page

CSS = pathlib.Path(__file__).resolve().parents[3] / 'cards' / 'static' / 'cards' / 'css' / 'cards.css'


class _View(CardMixin, TemplateView):
    pass


def _view():
    view = _View()
    view.request = RequestFactory().get('/')
    return view


def _everywhere(build):
    """Render ``build(card)`` in every pack and row template."""
    for pack in PACKS:
        with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
            for template_name in ROW_TEMPLATES:
                card = _view().add_card('probe', title='Probe', template_name=template_name)
                build(card)
                yield pack, template_name, card.render()


def _with_class(page, tag, css_class):
    return [a for a in page.find(tag) if css_class in (a.get('class') or '').split()]


class TestAddHeading(SimpleTestCase):

    def test_a_heading_and_its_note(self):
        for pack, template_name, html in _everywhere(lambda c: c.add_heading('Activity', note='65 logins')):
            with self.subTest(pack=pack, template=template_name):
                page = _Page(html)
                titles = _with_class(page, 'span', 'django-card__heading-title')
                self.assertEqual(len(titles), 1, html)
                self.assertEqual(titles[0]['role'], 'heading')
                self.assertEqual(len(_with_class(page, 'span', 'django-card__heading-note')), 1)
                self.assertIn('Activity', ''.join(page.text))
                self.assertIn('65 logins', ''.join(page.text))

    def test_no_note_draws_none(self):
        for pack, template_name, html in _everywhere(lambda c: c.add_heading('Account')):
            with self.subTest(pack=pack, template=template_name):
                self.assertNotIn('django-card__heading-note', html)

    def test_a_note_of_zero_is_shown_and_a_title_is_needed(self):
        card = _view().add_card('probe', title='Probe').add_heading('Open', note=0)
        self.assertEqual(len(_with_class(_Page(card.render()), 'span', 'django-card__heading-note')), 1)
        with self.assertRaisesMessage(ValueError, 'needs a title'):
            card.add_heading(None)

    def test_escaped_unless_marked_safe(self):
        def build(card):
            card.add_heading('<b class="x">A</b>', note='<i class="y">n</i>')
            card.add_heading(mark_safe('<b class="safe">B</b>'))

        for pack, template_name, html in _everywhere(build):
            with self.subTest(pack=pack, template=template_name):
                page = _Page(html)
                self.assertEqual(page.find('b', **{'class': 'x'}), [])
                self.assertEqual(page.find('i', **{'class': 'y'}), [])
                self.assertEqual(len(page.find('b', **{'class': 'safe'})), 1)

    def test_it_chains_and_asks_for_the_stylesheet(self):
        card = _view().add_card('probe', title='Probe')
        self.assertIs(card.add_heading('A'), card)
        self.assertTrue(card.requires_card_css)
        self.assertIn('cards/css/cards.css', card.render())


class TestAddFacts(SimpleTestCase):

    @staticmethod
    def build(card):
        card.add_facts(
            {'title': 'Status', 'entries': [
                {'label': 'State', 'value': 'Confirmed', 'badge': 'bg-success'},
                {'label': 'Stage', 'value': 'Delivery'},
                {'label': 'Type', 'value': 'External'},
            ]},
            {'title': 'Sell', 'lead': '£5,800.00', 'entries': [{'label': 'Inc tax', 'value': '£6,960.00'}]},
        )

    def test_columns_hold_their_own_facts_top_to_bottom(self):
        for pack, template_name, html in _everywhere(self.build):
            with self.subTest(pack=pack, template=template_name):
                page = _Page(html)
                self.assertEqual(len(_with_class(page, 'div', 'django-card__facts')), 1, html)
                self.assertEqual(len(_with_class(page, 'div', 'django-card__facts-col')), 2)
                titles = _with_class(page, 'div', 'django-card__facts-title')
                self.assertEqual(len(titles), 2)
                self.assertEqual(len(_with_class(page, 'div', 'django-card__fact')), 5)  # 3 + the lead + 1
                self.assertEqual(len(_with_class(page, 'div', 'django-card__fact--lead')), 1)
                # column-major: Status's three facts come before Sell's heading
                self.assertLess(html.index('External'), html.index('>Sell<'))
                self.assertLess(html.index('>Sell<'), html.index('5,800.00'))
                self.assertEqual(len(_with_class(page, 'span', 'badge')), 1)
                # a fact is not a list item of its own: only the row around the columns is one
                items = _with_class(page, 'div', 'list-group-item')
                self.assertEqual(len(items), 1 if template_name == 'default' else 0, html)

    def test_a_fact_is_drawn_as_a_rows_entry_is(self):
        """Same markup as add_row's: a menu by the label, a default for a missing value."""
        def build(card):
            card.add_facts({'title': 'Team', 'entries': [
                {'label': 'Salesman', 'value': None, 'default': 'Not set',
                 'menu': [HtmlMenuItem('<b class="probe-edit">Edit</b>')]},
            ]})

        for pack, template_name, html in _everywhere(build):
            with self.subTest(pack=pack, template=template_name):
                page = _Page(html)
                self.assertEqual(len(page.find('b', **{'class': 'probe-edit'})), 1, html)
                self.assertIn('Not set', ''.join(page.text))
                self.assertEqual(len(page.find('label')), 1)

    def test_a_field_name_reads_the_details_object(self):
        card = _view().add_card('probe', title='Probe', details_object=Company(name='Cedarlite', number='5879'))
        card.add_facts({'title': 'Account', 'entries': ['name', 'number']})
        text = ''.join(_Page(card.render()).text)
        self.assertIn('Cedarlite', text)
        self.assertIn('5879', text)

    def test_a_hidden_fact_is_left_out_and_extra_row_kwargs_reach_every_fact(self):
        card = _view().add_card('probe', title='Probe')
        card.add_facts({'entries': [{'label': 'Shown', 'value': 'a'},
                                    {'label': 'Gone', 'value': 'b', 'hidden': True}]},
                       extra_row_kwargs={'css_class': 'probe-value'})
        page = _Page(card.render())
        self.assertEqual(len(_with_class(page, 'div', 'django-card__fact')), 1)
        self.assertNotIn('Gone', ''.join(page.text))
        self.assertEqual(len(_with_class(page, 'h4', 'probe-value')), 1)
        # an entry's own entry_css_class is added to the fact's, which carries its layout
        card.add_facts({'entries': [{'label': 'Own', 'value': 'c', 'entry_css_class': 'mine'}]})
        mine = _with_class(_Page(card.render()), 'div', 'mine')
        self.assertEqual(len(mine), 1)
        self.assertIn('django-card__fact', mine[0]['class'].split())

    def test_a_cards_default_row_style_is_for_its_rows_not_its_facts(self):
        card = _view().add_card('probe', title='Probe')
        card.add_row_style('styled', '<div class="probe-style">{label}:{value}</div>', is_default=True)
        card.add_entry(label='Row', value='r')
        card.add_facts({'title': 'T', 'lead': '£5', 'entries': [{'label': 'L', 'value': 'V'}]})
        card.add_facts({'entries': [{'label': 'Own', 'value': 'o', 'row_style': 'styled'}]})
        html = card.render()
        page = _Page(html)
        self.assertEqual(len(_with_class(page, 'div', 'probe-style')), 2, html)  # the row, and the fact that asked
        self.assertEqual(len(_with_class(page, 'div', 'django-card__fact--lead')), 1)
        self.assertNotIn('None', html)
        # and the default is still in place for the rows added after
        card.add_entry(label='After', value='a')
        self.assertEqual(len(_with_class(_Page(card.render()), 'div', 'probe-style')), 3)

    def test_no_columns_add_no_row(self):
        card = _view().add_card('probe', title='Probe')
        card.add_facts()
        self.assertEqual(card.rows, [])

    def test_a_lead_can_be_a_dict_of_entry_options(self):
        card = _view().add_card('probe', title='Probe')
        card.add_facts({'title': 'Sell', 'lead': {'value': '£1.00', 'css_class': 'probe-lead'}})
        page = _Page(card.render())
        self.assertEqual(len(_with_class(page, 'div', 'django-card__fact--lead')), 1)
        self.assertIn('£1.00', ''.join(page.text))

    def test_titles_and_values_are_escaped(self):
        def build(card):
            card.add_facts({'title': '<b class="x">T</b>', 'lead': '<i class="y">L</i>',
                            'entries': [{'label': '<u class="z">K</u>', 'value': '<s class="w">V</s>'}]})

        for pack, template_name, html in _everywhere(build):
            with self.subTest(pack=pack, template=template_name):
                page = _Page(html)
                for tag, cls in (('b', 'x'), ('i', 'y'), ('u', 'z'), ('s', 'w')):
                    self.assertEqual(page.find(tag, **{'class': cls}), [], (tag, html))

    def test_wrong_shapes_are_refused(self):
        card = _view().add_card('probe', title='Probe')
        with self.assertRaisesMessage(ValueError, 'one dict per column'):
            card.add_facts(['name'])
        with self.assertRaisesMessage(ValueError, 'are a list'):
            card.add_facts({'entries': 'name'})
        with self.assertRaisesMessage(ValueError, 'a field name or a dict'):
            card.add_facts({'entries': [42]})

    def test_a_section_stack_takes_no_facts_or_heading(self):
        view = _view()
        stack = view.add_card('stack', title='Stack')
        stack.add_sections([view.add_card('inner', title='Inner')])
        with self.assertRaises(ValueError):
            stack.add_facts({'entries': []})
        with self.assertRaises(ValueError):
            stack.add_heading('A')

    def test_export_takes_the_facts_and_skips_the_heading(self):
        card = _view().add_card('probe', title='Probe')
        card.add_heading('Account')
        card.add_facts({'title': 'Sell', 'lead': '£5', 'entries': [{'label': 'Inc tax', 'value': '£6'}]})
        self.assertEqual(card.get_export_data(), [{'label': '', 'value': '£5'}, {'label': 'Inc tax', 'value': '£6'}])

    def test_the_styling(self):
        css = CSS.read_text()
        grid = css[css.index('.django-card__facts {'):]
        self.assertIn('display: grid;', grid[:grid.index('}')])
        self.assertIn('auto-fit', grid[:grid.index('}')])
        # a fact's menu sits by its label, not at the column's far edge
        beside = css[css.index('.django-card__fact > .d-flex {'):]
        self.assertIn('justify-content: flex-start;', beside[:beside.index('}')])
        self.assertIn('.django-card__fact > .d-flex > label,\n.django-card__fact > .d-flex > .list-group-item-heading {\n'
                      '    margin-right: 0 !important;', css)
