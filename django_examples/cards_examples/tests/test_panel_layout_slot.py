"""A panel layout with a slot for the page's own content: ``add_slot()`` and ``render_around()``.

A layout whose main region holds whatever the page renders itself -- a ``{% block %}`` that every
page using the layout fills differently -- cannot hold that content as a card. So the layout leaves
a slot (a region's or tab's ``add_slot()``, or ``{% panel_slot %}`` inside a card's own template),
``render_around()`` splits the rendered layout there, and the page prints its content between the
halves -- by hand, or with ``{% panel_layout_around layout %}...{% endpanel_layout_around %}``.

None or two slots raise: the content would be lost or drawn twice, with nothing to say why.

The marker is an html comment named by a random nonce made once per request, so stored rich text
printed safe in a card cannot carry it: text stored before this request cannot know it, and one
read off a page is useless to the next request.
"""
from django.template import Context, Engine, Template
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.views.generic import TemplateView

from cards import render_scope
from cards.panel_layout import PanelLayoutParts, slot_marker
from cards.standard import CardMixin
from cards_examples.tests.test_escaping import PACKS, _Page


class _CardView(CardMixin, TemplateView):
    pass


def _view():
    view = _CardView()
    view.request = RequestFactory().get('/')
    return view


def _layout(view, build_main):
    layout = view.add_panel_layout(card_name='shell', persist=False)
    side = view.add_card('side', title='Side')
    side.add_entry(value='side text', label='Side')
    layout.root.add_region('side', size='240px').add_card(side)
    build_main(layout.root.add_region('main', size='1fr'))
    return layout


def _region_slot(view):
    return _layout(view, lambda main: main.add_slot())


class TestRenderAround(SimpleTestCase):

    def test_the_page_content_lands_in_the_slot_region(self):
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                with self.subTest(pack=pack):
                    view = _view()
                    parts = _region_slot(view).render_around()
                    self.assertIsInstance(parts, PanelLayoutParts)
                    html = f'{parts.before}<p class="page-content">mine</p>{parts.after}'
                    page = _Page(html)
                    self.assertEqual(len(page.find('p', **{'class': 'page-content'})), 1)
                    self.assertNotIn(slot_marker(), html)
                    # the content sits in the main region's content, after the side region's card
                    self.assertLess(html.index('side text'), html.index('page-content'))
                    self.assertLess(html.index('id="panel_region_main"'), html.index('page-content'))
                    # and the layout's markup closes after it: both halves are real halves
                    self.assertTrue(parts.before.strip() and parts.after.strip())
                    self.assertGreater(parts.after.count('</div>'), 2)

    def test_a_tab_can_hold_the_slot(self):
        view = _view()
        layout = _layout(view, lambda main: main.add_tab('one', title='One').add_slot())
        parts = layout.render_around()
        self.assertIn('panel_tab_main_one', parts.before)

    def test_a_cards_own_template_can_hold_the_slot(self):
        """The page's content inside a card's body, under what the card draws itself."""
        engine = Engine.get_default()

        def main(region):
            view = region_view['view']
            html = Template('{% load django_cards_tags %}<div class="shell-strip">strip</div>{% panel_slot %}',
                            engine=engine).render(Context())
            region.add_card(view.add_html_data_card(card_name='shell_card', title='Shell', html=html))

        region_view = {'view': _view()}
        parts = _layout(region_view['view'], main).render_around()
        self.assertIn('shell-strip', parts.before)
        self.assertNotIn('shell-strip', parts.after)

    def test_no_slot_raises(self):
        view = _view()
        layout = _layout(view, lambda main: main.add_card(view.add_card('plain', title='Plain')))
        with self.assertRaisesMessage(ValueError, 'no slot'):
            layout.render_around()

    def test_two_slots_raise(self):
        """In two regions: caught when the page renders."""
        view = _view()
        layout = view.add_panel_layout(card_name='shell', persist=False)
        layout.root.add_region('a', size='1fr').add_slot()
        layout.root.add_region('b', size='1fr').add_slot()
        with self.assertRaisesMessage(ValueError, '2 slots'):
            layout.render_around()

    def test_a_second_slot_in_one_region_or_tab_raises_as_it_is_added(self):
        view = _view()
        layout = view.add_panel_layout(card_name='shell', persist=False)
        region = layout.root.add_region('main', size='1fr')
        region.add_slot()
        with self.assertRaisesMessage(ValueError, "'main' already holds a slot"):
            region.add_slot()
        tab = layout.root.add_region('side', size='1fr').add_tab('one', title='One')
        tab.add_slot()
        with self.assertRaises(ValueError):
            tab.add_slot()

    def test_it_registers_no_card_on_the_view(self):
        """It renders while the page does: adding to the view's cards then would change a dict the
        template may be reading, and could replace a card of the same name."""
        view = _view()
        layout = _region_slot(view)
        before = dict(view.cards)
        layout.render_around()
        layout.render_around()
        self.assertEqual(view.cards, before)

    def test_it_needs_no_view(self):
        from cards.panel_layout import PanelLayout
        layout = PanelLayout(card_name='bare')
        layout.root.add_region('main', size='1fr').add_slot()
        parts = layout.render_around()
        self.assertIn('panel_layout_bare', parts.before)


class _Request:
    """One request cycle's render scope, as django's request signals open and close it."""

    def __enter__(self):
        render_scope._open_scope()
        return self

    def __exit__(self, *exc):
        render_scope._close_scope()


class TestTheMarkerCannotBeForged(SimpleTestCase):

    def test_one_marker_per_request_and_a_new_one_for_the_next(self):
        with _Request():
            first = slot_marker()
            self.assertEqual(slot_marker(), first)
        with _Request():
            self.assertNotEqual(slot_marker(), first)
        self.assertRegex(first, r'^<!--django-cards-panel-slot-[0-9a-f]{24}-->$')

    def test_stored_text_holding_a_marker_is_not_a_slot(self):
        """A fixed marker, or one read off an earlier page, stored and printed safe in a card."""
        from django.utils.safestring import mark_safe
        with _Request():
            leaked = slot_marker()
        for stored in ('<!--django-cards-panel-slot-->', leaked):
            with self.subTest(stored=stored), _Request():
                view = _view()
                layout = view.add_panel_layout(card_name='shell', persist=False)
                side = view.add_html_data_card(card_name='notes', title='Notes',
                                               html=mark_safe(f'<p class="stored">notes{stored}</p>'))
                layout.root.add_region('side', size='240px').add_card(side)
                layout.root.add_region('main', size='1fr').add_slot()
                parts = layout.render_around()
                # split at the real slot, in the main region, not in the stored text
                self.assertIn('class="stored"', parts.before)
                self.assertIn('id="panel_region_main"', parts.before)

    def test_a_slot_rendered_early_in_the_request_is_found(self):
        """{% panel_slot %} in an html card is rendered when the card is added, in setup_cards."""
        engine = Engine.get_default()
        with _Request():
            view = _view()
            html = Template('{% load django_cards_tags %}<div class="strip">strip</div>{% panel_slot %}',
                            engine=engine).render(Context())

            def main(region):
                region.add_card(view.add_html_data_card(card_name='shell_card', title='Shell', html=html))

            parts = _layout(view, main).render_around()
            self.assertIn('class="strip"', parts.before)

    def test_a_nested_layouts_slot_is_found(self):
        """A layout rendered as a card inside another keeps its slot for the outer one to split."""
        with _Request():
            view = _view()
            inner = view.add_panel_layout(card_name='inner', persist=False)
            inner.root.add_region('inner_main', size='1fr').add_slot()
            outer = view.add_panel_layout(card_name='outer', persist=False)
            outer.root.add_region('outer_main', size='1fr').add_card(inner.render())
            parts = outer.render_around()
            self.assertIn('id="panel_region_inner_main"', parts.before)


class TestPanelLayoutAroundTag(SimpleTestCase):

    def test_the_tag_puts_its_contents_in_the_slot(self):
        layout = _region_slot(_view())
        html = Template('{% load django_cards_tags %}'
                        '{% panel_layout_around layout %}<p class="page-content">{{ word }}</p>{% endpanel_layout_around %}'
                        ).render(Context({'layout': layout, 'word': 'mine & yours'}))
        self.assertEqual(len(_Page(html).find('p', **{'class': 'page-content'})), 1)
        self.assertIn('mine &amp; yours', html)
        self.assertIn('side text', html)
        self.assertNotIn(slot_marker(), html)

    def test_a_child_templates_block_fills_the_slot(self):
        """A base template can wrap every child page's content in the layout."""
        engine = Engine(
            loaders=[('django.template.loaders.locmem.Loader', {
                'base.html': '{% load django_cards_tags %}'
                             '{% panel_layout_around layout %}{% block content %}base{% endblock %}'
                             '{% endpanel_layout_around %}',
                'child.html': '{% extends "base.html" %}{% block content %}<p class="child">child</p>{% endblock %}',
            })],
            libraries={'django_cards_tags': 'cards.templatetags.django_cards_tags'},
        )
        html = engine.get_template('child.html').render(Context({'layout': _region_slot(_view())}))
        self.assertEqual(len(_Page(html).find('p', **{'class': 'child'})), 1, html)
        self.assertNotIn('>base<', html)
        self.assertIn('side text', html)

    def test_a_missing_layout_says_so(self):
        from django.template import TemplateSyntaxError
        t = Template('{% load django_cards_tags %}{% panel_layout_around view.layuot %}x{% endpanel_layout_around %}')
        with self.assertRaisesMessage(TemplateSyntaxError, "needs a PanelLayout; 'view.layuot'"):
            t.render(Context({'view': object()}))

    def test_it_takes_one_argument(self):
        from django.template import TemplateSyntaxError
        with self.assertRaises(TemplateSyntaxError):
            Template('{% load django_cards_tags %}{% panel_layout_around %}x{% endpanel_layout_around %}')
