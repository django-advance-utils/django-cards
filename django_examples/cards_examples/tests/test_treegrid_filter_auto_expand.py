"""treegrid_filter_auto_expand has to reach the card's config.

add_treegrid_card has accepted it since 1.4.x and defaults it to True, but nothing wrote it
into extra_card_info, so the template's lookup resolved to '' and every grid rendered it
false. These pin both ends: the default, and a caller who turns it off.
"""
from django.test import RequestFactory, TestCase
from django.views.generic import TemplateView

from cards.standard import CardMixin
from cards_examples.tests import SIMPLE_COLUMNS, simple_nodes


class FilterAutoExpandView(CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'
    filter_auto_expand = True

    def setup_cards(self):
        self.add_treegrid_card(
            card_name='grid',
            title='Grid',
            treegrid_columns=SIMPLE_COLUMNS,
            treegrid_static_data=simple_nodes('grid'),
            treegrid_filter_auto_expand=self.filter_auto_expand,
        )
        self.add_card_group('grid')


class DefaultFilterAutoExpandView(FilterAutoExpandView):
    """The kwarg left alone, so add_treegrid_card's own default is what lands."""

    def setup_cards(self):
        self.add_treegrid_card(
            card_name='grid',
            title='Grid',
            treegrid_columns=SIMPLE_COLUMNS,
            treegrid_static_data=simple_nodes('grid'),
        )
        self.add_card_group('grid')


class TestTreegridFilterAutoExpand(TestCase):

    @staticmethod
    def _html(view_class, **attrs):
        request = RequestFactory().get('/treegrid/')
        response = view_class.as_view(**attrs)(request)
        response.render()
        return response.content.decode()

    def test_on_by_default(self):
        self.assertIn('filter_auto_expand: true', self._html(DefaultFilterAutoExpandView))

    def test_a_caller_can_turn_it_off(self):
        html = self._html(FilterAutoExpandView, filter_auto_expand=False)
        self.assertIn('filter_auto_expand: false', html)

    def test_a_caller_can_turn_it_on(self):
        html = self._html(FilterAutoExpandView, filter_auto_expand=True)
        self.assertIn('filter_auto_expand: true', html)
