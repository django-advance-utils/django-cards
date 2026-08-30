"""A 1.4.x template copied into a project and left there has to be loud, not silent.

Two shapes go wrong on upgrade, and they fail in opposite directions, so one check cannot
cover both:

- a copied ``treegrid.html`` pulls the shared behaviour in per card and never includes
  ``_treegrid_init.html``, so no config is ever emitted -- nothing queues, and the queued
  config warning has nothing to fire on;
- a copied ``_treegrid_script.html`` overrides the shared half with per-card code that
  defines no shared behaviour, so every card's config queues and nothing drains it.

The tests below prove which check each shape reaches, by way of what the page carries.
"""
import os

from django.conf import settings
from django.test import RequestFactory, TestCase, override_settings
from django.views.generic import TemplateView

from cards.standard import CardMixin
from cards.templatetags.django_cards_tags import _shared_assets_cached
from cards_examples.tests import (CONFIG_BLOCK, FACTORY, QUEUE_WARN, SHARED_CHECK,
                                  SIMPLE_COLUMNS, simple_nodes)

HERE = os.path.dirname(os.path.abspath(__file__))
STALE_TREEGRID_HTML = os.path.join(HERE, 'stale_treegrid_html')
STALE_TREEGRID_SCRIPT = os.path.join(HERE, 'stale_treegrid_script')


class TwoTreegridsView(CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        for name in ('left', 'right'):
            self.add_treegrid_card(
                card_name=name,
                title=name.title(),
                treegrid_columns=SIMPLE_COLUMNS,
                treegrid_static_data=simple_nodes(name),
            )
            self.add_card_group(name, div_css_class='col-6 float-left')


def _override_dir(path):
    """The project's template dir ahead of the app ones, the way an override is installed."""
    templates = [{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [path],
        'APP_DIRS': True,
        'OPTIONS': {'context_processors': settings.TEMPLATES[0]['OPTIONS']['context_processors']},
    }]
    return override_settings(TEMPLATES=templates)


class StaleOverrideTestMixin:
    """Renders the two-card page with a stale copy installed as a project template."""

    override_dir = None

    def setUp(self):
        # The shared half is cached for the life of the process, so an override installed
        # mid-run would otherwise render behind whatever a previous test cached.
        _shared_assets_cached.cache_clear()
        self.addCleanup(_shared_assets_cached.cache_clear)

    def _html(self):
        with _override_dir(self.override_dir):
            request = RequestFactory().get('/treegrid/')
            response = TwoTreegridsView.as_view()(request)
            response.render()
            return response.content.decode()


class TestStaleTreegridHtml(StaleOverrideTestMixin, TestCase):
    """A project copy of the 1.4.x treegrid.html: shared behaviour, nothing to call it."""

    override_dir = STALE_TREEGRID_HTML

    def test_the_shared_behaviour_still_arrives(self):
        """Per card, the way 1.4.x shipped it -- the copy knows nothing about sharing."""
        self.assertEqual(self._html().count(FACTORY), 2)

    def test_no_card_emits_a_config(self):
        """The copy never includes _treegrid_init.html, so there is nothing to initialise."""
        self.assertEqual(self._html().count(CONFIG_BLOCK), 0)

    def test_the_queued_config_warning_cannot_fire(self):
        """No config means no queue: this shape is invisible to the check in _treegrid_init."""
        self.assertNotIn(QUEUE_WARN, self._html())

    def test_the_shared_half_reports_that_nothing_called_it(self):
        self.assertIn(SHARED_CHECK, self._html())


class TestStaleTreegridScript(StaleOverrideTestMixin, TestCase):
    """A project copy of the 1.4.x _treegrid_script.html: configs, no shared behaviour."""

    override_dir = STALE_TREEGRID_SCRIPT

    def test_the_override_is_what_gets_rendered(self):
        html = self._html()
        self.assertIn('window._staleTreegridScriptRan', html)
        self.assertNotIn(FACTORY, html)

    def test_every_card_still_emits_its_config(self):
        self.assertEqual(self._html().count(CONFIG_BLOCK), 2)

    def test_the_queued_config_warning_is_the_one_that_fires(self):
        html = self._html()
        self.assertIn(QUEUE_WARN, html)
        self.assertNotIn(SHARED_CHECK, html)
