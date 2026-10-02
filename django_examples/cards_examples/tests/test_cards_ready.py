"""The cards_ready() hook: once every card exists, before any of them is rendered.

A subclass that builds a card after its own super().setup_cards() call returns leaves a
setup_cards() override further up the chain no way to reach that card. cards_ready() runs once
the whole chain has returned, wherever the view builds all its cards to render them.
"""
import json

from ajax_helpers.mixins import AjaxHelpers
from django.test import RequestFactory, TestCase
from django.views.generic import TemplateView

from cards.standard import CardMixin


class _RetitleOnceReady(CardMixin):
    """What a base view uses the hook for: reaching a card that a subclass builds late."""

    def cards_ready(self):
        super().cards_ready()
        card = self.cards.get('late')
        if card is not None:
            card.title = 'Ready'


class _LateCardView(_RetitleOnceReady, AjaxHelpers, TemplateView):
    def __init__(self, *args, **kwargs):
        self.calls = []
        super().__init__(*args, **kwargs)

    def setup_datatable_cards(self):
        self.calls.append('setup_datatable_cards')
        super().setup_datatable_cards()

    def setup_cards(self):
        # The base's setup_cards runs here, before the card below exists.
        super().setup_cards()
        self.add_card('late', title='Built late')
        self.add_card_group('late', div_css_class='col-12')
        self.calls.append('setup_cards')

    def cards_ready(self):
        self.calls.append('cards_ready')
        super().cards_ready()

    def render_card_groups(self, card_groups):
        self.calls.append('render_card_groups')
        return super().render_card_groups(card_groups)


class _PlainView(CardMixin, TemplateView):
    def setup_cards(self):
        self.add_card('plain', title='Plain')
        self.add_card_group('plain', div_css_class='col-12')


class _PanelRegionCardView(_RetitleOnceReady, TemplateView):
    """The card the base retitles sits in a panel layout region, and layout.render() runs in setup_cards()."""

    def setup_cards(self):
        super().setup_cards()
        layout = self.add_panel_layout()
        region = layout.root.add_region('main')
        region.add_card(self.add_card('late', title='Built late'))
        self.add_card_group(layout.render(), div_css_class='col-12')


class TestCardsReady(TestCase):
    def setUp(self):
        self.view = _LateCardView()
        self.view.request = RequestFactory().get('/')

    def test_a_card_built_after_the_setup_chain_is_reached_before_it_renders(self):
        html = self.view.get_context_data()['card_groups']['main']
        self.assertIn('Ready', html)
        self.assertNotIn('Built late', html)

    def test_a_card_in_a_panel_layout_region_is_reached_before_it_renders(self):
        view = _PanelRegionCardView()
        view.request = RequestFactory().get('/')
        html = view.get_context_data()['card_groups']['main']
        self.assertIn('Ready', html)
        self.assertNotIn('Built late', html)

    def test_it_runs_after_every_setup_and_before_anything_renders(self):
        self.view.get_context_data()
        self.assertEqual(
            self.view.calls, ['setup_datatable_cards', 'setup_cards', 'cards_ready', 'render_card_groups']
        )

    def test_a_card_reload_runs_it_too(self):
        response = self.view.button_reload_card(card='late')
        html = next(command['html'] for command in json.loads(response.content) if command.get('html'))
        self.assertIn('Ready', html)
        self.assertNotIn('Built late', html)

    def test_an_accordion_load_runs_it_too(self):
        self.view.button_accordion_load(accordion='none', panel_id='none')
        self.assertEqual(self.view.calls, ['setup_datatable_cards', 'setup_cards', 'cards_ready'])

    def test_by_default_it_changes_nothing(self):
        view = _PlainView()
        view.request = RequestFactory().get('/')
        self.assertIn('Plain', view.get_context_data()['card_groups']['main'])

    def test_a_handler_of_your_own_gets_it_from_build_cards(self):
        self.view.build_cards()
        self.assertEqual(self.view.calls, ['setup_datatable_cards', 'setup_cards', 'cards_ready'])
        self.assertEqual(self.view.cards['late'].title, 'Ready')

    def test_rebuild_cards_starts_from_nothing_and_runs_it_again(self):
        self.view.build_cards()
        self.view.cards['stale'] = self.view.cards['late']
        self.view.rebuild_cards()
        self.assertNotIn('stale', self.view.cards)
        self.assertEqual(self.view.calls, ['setup_datatable_cards', 'setup_cards', 'cards_ready'] * 2)
        self.assertEqual(self.view.cards['late'].title, 'Ready')
