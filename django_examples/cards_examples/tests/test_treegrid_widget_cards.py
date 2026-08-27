"""The jms_cloud shape: four treegrid form widgets, each building its own card mixin, so
none of the cards has a request. Rendered through the test client so the request cycle
signals fire the way they do under a real server.
"""
from django.forms import CharField, Form
from django.forms.widgets import TextInput
from django.template.response import TemplateResponse
from django.test import TestCase, RequestFactory
from django.urls import path
from django.views.generic import TemplateView

from cards.standard import CardMixin
from cards_examples.tests import FACTORY, INIT_CALL, STYLE_RULE, SIMPLE_COLUMNS, simple_nodes


class TreeGridWidget(TextInput):
    """A stand-in for jms_cloud's widget: it builds its own mixin, so no request."""

    template_name = 'cards_examples/widget_tree_grid.html'

    def __init__(self, tree_grid_kwargs, **kwargs):
        self.tree_grid_kwargs = tree_grid_kwargs
        super().__init__(**kwargs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        mixin = CardMixin()            # nothing to give it a request
        context['tree_grid_card'] = mixin.add_treegrid_card(
            **self.tree_grid_kwargs, treegrid_form_field=name)
        return context


class FourFiltersForm(Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for n in range(1, 5):
            code = f'filter{n}'
            self.fields[code] = CharField(
                label=f'Filter {n}',
                required=False,
                widget=TreeGridWidget(tree_grid_kwargs=dict(
                    card_name=f'{code}_tree_filter',
                    title=f'Filter {n}',
                    treegrid_columns=SIMPLE_COLUMNS,
                    treegrid_static_data=simple_nodes(code),
                    treegrid_checkbox=True,
                )),
            )


class FourFiltersView(TemplateView):
    template_name = 'cards_examples/widget_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = FourFiltersForm()
        return context


urlpatterns = [path('four-filters/', FourFiltersView.as_view(), name='four_filters')]


class TestWidgetBuiltCards(TestCase):
    """Cards with no request of their own still share one copy per page."""

    def _html_via_client(self):
        with self.settings(ROOT_URLCONF=__name__):
            response = self.client.get('/four-filters/')
            self.assertEqual(response.status_code, 200)
            return response.content.decode()

    def test_all_four_grids_are_on_the_page(self):
        html = self._html_via_client()
        for n in range(1, 5):
            self.assertIn(f'id="filter{n}_tree_filter_table"', html)
            self.assertIn(f"card_code: 'filter{n}_tree_filter'", html)

    def test_behaviour_emitted_once_for_four_request_less_cards(self):
        self.assertEqual(self._html_via_client().count(FACTORY), 1)

    def test_stylesheet_emitted_once_for_four_request_less_cards(self):
        self.assertEqual(self._html_via_client().count(STYLE_RULE), 1)

    def test_one_init_call_per_card(self):
        self.assertEqual(self._html_via_client().count(INIT_CALL), 4)

    def test_four_grids_cost_far_less_than_four_copies(self):
        """The measurement this split is for: about 460 KiB of HTML became about 130 KiB."""
        with_cycle = len(self._html_via_client())
        with self.settings(ROOT_URLCONF=__name__):
            request = RequestFactory().get('/four-filters/')
            response = FourFiltersView.as_view()(request)
            response.render()
        self.assertLess(with_cycle, len(response.content) / 3)

    def test_a_second_page_carries_it_again(self):
        """Each request is its own page, so the next one is not left without it."""
        first = self._html_via_client()
        second = self._html_via_client()
        self.assertEqual(first.count(FACTORY), 1)
        self.assertEqual(second.count(FACTORY), 1)

    def test_without_the_request_cycle_it_still_renders_every_grid(self):
        """RequestFactory fires no signals, so there is no scope: the safe path.

        Each card still gets its behaviour -- more copies than needed, never none.
        """
        with self.settings(ROOT_URLCONF=__name__):
            request = RequestFactory().get('/four-filters/')
            response = FourFiltersView.as_view()(request)
            self.assertIsInstance(response, TemplateResponse)
            response.render()
            html = response.content.decode()
        self.assertEqual(html.count(INIT_CALL), 4)
        self.assertEqual(html.count(FACTORY), 4)
