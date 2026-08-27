"""A project may wrap cards/standard/treegrid.html to append its own overrides.

jms_cloud does exactly this, so the wrapper has to keep working: one shared stylesheet for the
page, one copy of the behaviour, and every card's override CSS still after the shared
stylesheet so its !important rules win.
"""
from django.test import TestCase
from django.urls import path
from django.views.generic import TemplateView

from cards.standard import CardMixin
from cards_examples.tests import FACTORY, INIT_CALL, STYLE_RULE, SIMPLE_COLUMNS, simple_nodes

OVERRIDE_RULE = 'color: #123456 !important;'


class WrappedTreegridsView(CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        for name in ('left', 'right'):
            self.add_treegrid_card(
                card_name=name,
                title=name.title(),
                template_name='cards_examples/wrapped_treegrid.html',
                treegrid_columns=SIMPLE_COLUMNS,
                treegrid_static_data=simple_nodes(name),
                treegrid_checkbox=True,
            )
            self.add_card_group(name, div_css_class='col-6 float-left')


urlpatterns = [path('wrapped/', WrappedTreegridsView.as_view(), name='wrapped')]


class TestWrappedTreegridTemplate(TestCase):

    def _html(self):
        with self.settings(ROOT_URLCONF=__name__):
            response = self.client.get('/wrapped/')
            self.assertEqual(response.status_code, 200)
            return response.content.decode()

    def test_both_wrapped_cards_render(self):
        html = self._html()
        self.assertIn('id="left_table"', html)
        self.assertIn('id="right_table"', html)

    def test_shared_half_still_lands_once(self):
        html = self._html()
        self.assertEqual(html.count(FACTORY), 1)
        self.assertEqual(html.count(STYLE_RULE), 1)
        self.assertEqual(html.count(INIT_CALL), 2)

    def test_every_override_comes_after_the_shared_stylesheet(self):
        """Same selectors, same !important: the later one wins, so it has to be the override."""
        html = self._html()
        self.assertEqual(html.count(OVERRIDE_RULE), 2)
        first_override = html.index(OVERRIDE_RULE)
        self.assertLess(html.index(STYLE_RULE), first_override)
