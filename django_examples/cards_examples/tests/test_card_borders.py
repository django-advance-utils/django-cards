from django.test import RequestFactory, TestCase
from django.views.generic import TemplateView

from cards.base import CARD_BORDER_NONE, CARD_BORDER_THIN, normalize_card_border
from cards.standard import CardMixin


class _BorderCardView(CardMixin, TemplateView):
    def build(self, **kwargs):
        return self.add_card('demo', title='Demo', **kwargs)


class TestNormalizeCardBorder(TestCase):
    def test_default_is_none(self):
        self.assertIsNone(normalize_card_border(None))
        self.assertIsNone(normalize_card_border('default'))

    def test_thin(self):
        self.assertEqual(normalize_card_border('thin'), CARD_BORDER_THIN)
        self.assertEqual(normalize_card_border('THIN'), CARD_BORDER_THIN)

    def test_none_aliases(self):
        self.assertEqual(normalize_card_border('none'), CARD_BORDER_NONE)
        self.assertEqual(normalize_card_border(False), CARD_BORDER_NONE)
        self.assertEqual(normalize_card_border(0), CARD_BORDER_NONE)
        self.assertEqual(normalize_card_border('off'), CARD_BORDER_NONE)

    def test_truthy_keeps_default_chrome(self):
        # The mirror of test_none_aliases: a caller flipping the option from a flag can
        # have the flag either way round, and border=True must not blow up.
        self.assertIsNone(normalize_card_border(True))
        self.assertIsNone(normalize_card_border(1))
        self.assertIsNone(normalize_card_border('true'))
        self.assertIsNone(normalize_card_border('on'))
        self.assertIsNone(normalize_card_border('1'))

    def test_unknown_raises(self):
        with self.assertRaises(ValueError):
            normalize_card_border('thick')


class TestCardBorderRender(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = _BorderCardView()
        self.view.request = self.factory.get('/')

    def test_default_has_no_border_class(self):
        html = self.view.build().render()
        self.assertIn('card django-card', html)
        self.assertNotIn('django-card--thin-border', html)
        self.assertNotIn('django-card--borderless', html)

    def test_thin_border_class_and_css(self):
        html = self.view.build(border='thin').render()
        self.assertIn('django-card--thin-border', html)
        self.assertIn('cards/css/cards.css', html)
        self.assertNotIn('django-card--borderless', html)

    def test_none_border_class(self):
        html = self.view.build(border='none', show_header=False).render()
        self.assertIn('django-card--borderless', html)
        self.assertIn('cards/css/cards.css', html)
        self.assertNotIn('django-card--thin-border', html)

    def test_false_is_borderless(self):
        html = self.view.build(border=False).render()
        self.assertIn('django-card--borderless', html)

    def test_true_renders_default_chrome(self):
        html = self.view.build(border=True).render()
        self.assertIn('card django-card', html)
        self.assertNotIn('django-card--thin-border', html)
        self.assertNotIn('django-card--borderless', html)

    def test_appends_to_extra_card_css_class(self):
        html = self.view.build(
            border='thin',
            extra_card_context={'card_css_class': 'card django-card my-extra'},
        ).render()
        self.assertIn('my-extra', html)
        self.assertIn('django-card--thin-border', html)

    def test_css_emitted_once_when_scope_marks_it(self):
        from cards.base import CARD_CSS_MARK, card_css_once
        from cards.render_scope import RenderScope, _current_scope

        token = _current_scope.set(RenderScope())
        try:
            first = card_css_once()
            second = card_css_once()
            self.assertIn('cards/css/cards.css', first)
            self.assertEqual(second, '')
            self.assertTrue(getattr(_current_scope.get(), CARD_CSS_MARK))
        finally:
            _current_scope.reset(token)

    def test_css_emitted_once_against_the_request_without_a_scope(self):
        # No render scope -- outside a request cycle the request itself carries the mark,
        # the same fallback the treegrid shared-asset tag uses.
        from cards.base import CARD_CSS_MARK, card_css_once
        from cards.render_scope import _current_scope

        token = _current_scope.set(None)
        try:
            request = self.factory.get('/')
            self.assertIn('cards/css/cards.css', card_css_once(request))
            self.assertEqual(card_css_once(request), '')
            self.assertTrue(getattr(request, CARD_CSS_MARK))
        finally:
            _current_scope.reset(token)


class TestCardBordersPage(TestCase):
    def test_example_page_renders_thin_and_borderless(self):
        response = self.client.get('/card-borders/')
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('django-card--thin-border', html)
        self.assertIn('django-card--borderless', html)
        self.assertIn('Purchase Order Details', html)
        self.assertIn('fa-print', html)
        self.assertIn('btn-outline-secondary', html)
        self.assertIn('fa-file-invoice', html)
        # Header icons are links, not buttons: a btn in the header row is ~31px against an
        # 18px title and stretches the compact header back to default height.
        self.assertIn('django-card__header-icon', html)
        # Exactly one copy: the stylesheet is injected before the first bordered card and
        # the render scope stops every later card on the page repeating it.
        self.assertEqual(html.count('cards/css/cards.css'), 1)
