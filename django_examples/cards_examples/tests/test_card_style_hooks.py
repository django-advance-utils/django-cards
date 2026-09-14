"""Inline style hooks and row classes on the standard and table templates.

These are the pieces a compact purchase-order style card needs that the html template
already had: a style on the card itself (width:fit-content), a style on the body
(max-height + overflow for a scrolling card), and a class on the table row so a line
can be highlighted.
"""
from django.test import RequestFactory, TestCase
from django.views.generic import TemplateView

from cards.standard import CardMixin


class _StyleCardView(CardMixin, TemplateView):
    def build(self, **kwargs):
        return self.add_card('demo', title='Demo', **kwargs)


class TestCardStyleHooks(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = _StyleCardView()
        self.view.request = self.factory.get('/')

    def test_default_template_takes_a_card_style(self):
        html = self.view.build(
            extra_card_context={'card_css_style': 'width:fit-content'}).render()
        self.assertIn('style="width:fit-content"', html)

    def test_default_template_takes_a_body_style(self):
        html = self.view.build(
            extra_card_context={'card_body_css_style': 'max-height:600px;overflow:auto'}).render()
        self.assertIn('style="max-height:600px;overflow:auto"', html)

    def test_table_template_takes_both_styles(self):
        card = self.view.build(
            template_name='table',
            extra_card_context={'card_css_style': 'width:fit-content',
                                'card_body_css_style': 'max-height:600px;overflow:auto'})
        card.add_entry(value='GBP', label='Currency')
        html = card.render()
        self.assertIn('style="width:fit-content"', html)
        self.assertIn('style="max-height:600px;overflow:auto"', html)

    def test_no_style_attribute_without_one(self):
        # The hook is opt-in: cards that pass nothing render exactly as before.
        html = self.view.build().render()
        self.assertNotIn('style=""', html)
        self.assertNotIn('<div class="card django-card" id="demo" data-title="" style', html)

    def test_entry_css_class_reaches_the_table_row(self):
        card = self.view.build(template_name='table')
        card.add_entry(value='Overdue', label='Status', css_class='table-warning')
        card.add_entry(value='GBP', label='Currency')
        html = card.render()
        self.assertIn('<tr class="table-warning">', html)
        # only the row that asked for it
        self.assertEqual(html.count('table-warning'), 1)

    def test_html_rows_keep_their_own_row_class(self):
        card = self.view.build(template_name='table')
        card.add_html_string_entry('<b>raw</b>', exclude_td=False)
        html = card.render()
        self.assertIn('cards-html-row', html)
