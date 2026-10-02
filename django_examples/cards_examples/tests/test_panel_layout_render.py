"""A panel layout renders its regions' cards when the layout's card renders, not in layout.render().

layout.render() is called inside setup_cards(). Rendering the regions' cards there would fix their
HTML before cards_ready() runs; deferring it puts them with every other card, after the setup chain.
The layout card carries a lazy string for its html, so code reading it still gets a string's behaviour.
"""
import json

from ajax_helpers.mixins import AjaxHelpers
from django.core.serializers.json import DjangoJSONEncoder
from django.test import RequestFactory, TestCase
from django.utils.functional import Promise
from django.views.generic import TemplateView

from cards.base import CardBase
from cards.standard import CardMixin


class _CountingCard(CardBase):
    renders = 0

    def _render_template(self, override_card_context=None):
        _CountingCard.renders += 1
        return super()._render_template(override_card_context)


class _LayoutView(CardMixin, AjaxHelpers, TemplateView):
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

    def _layout_html(self):
        self.view.setup_cards()
        return self.view.cards['panel_layout'].extra_card_info['html']

    def test_layout_render_builds_the_card_without_rendering_the_regions(self):
        html = self._layout_html()
        self.assertEqual(_CountingCard.renders, 0)
        self.assertIsInstance(html, Promise)

    def test_the_regions_render_with_the_layout_card(self):
        html = self.view.get_context_data()['card_groups']['main']
        self.assertIn('Inner card', html)
        self.assertIn('panel-layout', html)
        self.assertEqual(_CountingCard.renders, 2)  # the region card and the layout card

    def test_the_markup_is_not_escaped_and_reads_as_a_string(self):
        html = self._layout_html()
        self.assertIn('<div', str(html))
        self.assertEqual(str(html), html.__html__())

    def test_it_behaves_as_a_string_for_code_that_already_held_one(self):
        html = self._layout_html()
        rendered = str(html)
        self.assertEqual('<p>before</p>' + html + '<p>after</p>', '<p>before</p>' + rendered + '<p>after</p>')
        self.assertEqual(len(html), len(rendered))
        self.assertIn('Inner card', html)
        self.assertEqual(html, rendered)
        self.assertEqual(json.dumps({'html': html}, cls=DjangoJSONEncoder), json.dumps({'html': rendered}))

    def test_an_ajax_handler_can_send_it_as_a_command(self):
        html = self._layout_html()
        response = self.view.command_response('html', selector='#x', html=html)
        command = json.loads(response.content)[0]
        self.assertEqual(command['html'], str(html))

    def test_a_second_read_does_not_render_the_regions_again(self):
        html = self._layout_html()
        str(html)
        str(html)
        self.assertEqual(_CountingCard.renders, 1)
