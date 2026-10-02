"""A panel layout renders its regions' cards when the layout's card renders, not in layout.render().

layout.render() is called inside setup_cards(). Rendering the regions' cards there would fix their
HTML before cards_ready() runs; deferring it puts them with every other card, after the setup chain.
"""
from django.test import RequestFactory, TestCase
from django.views.generic import TemplateView

from cards.base import CardBase
from cards.panel_layout import DeferredLayoutHtml
from cards.standard import CardMixin


class _CountingCard(CardBase):
    renders = 0

    def _render_template(self, override_card_context=None):
        _CountingCard.renders += 1
        return super()._render_template(override_card_context)


class _LayoutView(CardMixin, TemplateView):
    card_cls = _CountingCard

    def setup_cards(self):
        layout = self.add_panel_layout()
        region = layout.root.add_region('main')
        region.add_card(self.add_card('inner', title='Inner card'))
        self.add_card_group(layout.render(), div_css_class='col-12')


class TestPanelLayoutRender(TestCase):
    def setUp(self):
        _CountingCard.renders = 0
        self.view = _LayoutView()
        self.view.request = RequestFactory().get('/')

    def test_layout_render_builds_the_card_without_rendering_the_regions(self):
        self.view.setup_cards()
        self.assertEqual(_CountingCard.renders, 0)
        self.assertIsInstance(self.view.cards['panel_layout'].extra_card_info['html'], DeferredLayoutHtml)

    def test_the_regions_render_with_the_layout_card(self):
        html = self.view.get_context_data()['card_groups']['main']
        self.assertIn('Inner card', html)
        self.assertIn('panel-layout', html)
        self.assertEqual(_CountingCard.renders, 2)  # the region card and the layout card

    def test_the_markup_is_not_escaped_and_reads_as_a_string(self):
        self.view.setup_cards()
        deferred = self.view.cards['panel_layout'].extra_card_info['html']
        self.assertIn('<div', str(deferred))
        self.assertEqual(str(deferred), deferred.__html__())

    def test_a_second_read_does_not_render_the_regions_again(self):
        self.view.setup_cards()
        deferred = self.view.cards['panel_layout'].extra_card_info['html']
        str(deferred)
        str(deferred)
        self.assertEqual(_CountingCard.renders, 1)
