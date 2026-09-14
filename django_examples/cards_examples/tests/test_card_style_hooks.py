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

    def test_no_style_attribute_without_one_on_the_table_template(self):
        card = self.view.build(template_name='table')
        card.add_entry(value='GBP', label='Currency')
        html = card.render()
        self.assertNotIn('style=""', html)
        self.assertNotIn('data-title="" style', html)

    def test_row_css_class_reaches_the_table_row(self):
        card = self.view.build(template_name='table')
        card.add_entry(value='Overdue', label='Status', row_css_class='table-warning')
        card.add_entry(value='GBP', label='Currency')
        html = card.render()
        self.assertIn('<tr class="table-warning">', html)
        # only the row that asked for it
        self.assertEqual(html.count('table-warning'), 1)

    def test_css_class_still_does_not_touch_the_table_row(self):
        # css_class means the value heading on the standard template; giving it a second
        # meaning here would silently restyle existing table cards, so the row needs its
        # own option and css_class keeps doing what it did.
        card = self.view.build(template_name='table')
        card.add_entry(value='Overdue', label='Status', css_class='text-danger')
        html = card.render()
        self.assertNotIn('<tr class="text-danger">', html)

    def test_row_css_class_lands_on_the_row_after_a_separator(self):
        # A separator closes the row it is on and opens the real one; the class has to
        # follow the content, not stay on the empty row left behind.
        card = self.view.build(template_name='table')
        card.add_entry(value='First', label='Before')
        card.add_entry(value='Second', label='After', separator=True,
                       row_css_class='table-warning')
        html = card.render()
        self.assertNotIn('<tr class="table-warning"> </tr>', ' '.join(html.split()))
        self.assertIn('table-warning', html)
        self.assertEqual(html.count('table-warning'), 1)
        # the class is on the row that actually holds the value
        body = ' '.join(html.split())
        row = body[body.index('table-warning'):]
        self.assertIn('Second', row[:400])

    def test_html_rows_keep_their_own_row_class(self):
        card = self.view.build(template_name='table')
        card.add_html_string_entry('<b>raw</b>', exclude_td=False)
        html = card.render()
        self.assertIn('cards-html-row', html)


class TestPurchaseOrderLayoutPage(TestCase):
    def test_example_page_renders_the_whole_layout(self):
        response = self.client.get('/purchase-order-layout/')
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('Purchase Order Details', html)
        self.assertIn('Delivery Address', html)
        self.assertIn('django-card--thin-border', html)
        self.assertIn('max-height:200px;overflow:auto', html)
        self.assertIn('width:fit-content', html)
        self.assertIn('<tr class="table-warning">', html)
        # blank values drop out rather than rendering an empty row
        self.assertNotIn('Free Issue', html)
        self.assertNotIn('Customer Sales Order', html)
        self.assertEqual(html.count('cards/css/cards.css'), 1)
        # Every header menu item on this page carries the icon class -- without it the
        # button chrome django-menus adds stretches the compact header back out. Counted
        # rather than asserted present, so dropping it from one card is caught too.
        self.assertEqual(html.count('django-card__header-icon'), 2)
