"""``card.add_sections(cards)``: a card whose body is a stack of folding sections, one per card.

Each section's header is a native toggle button holding the card's title and a chevron, with the
card's own menu beside it -- outside the button, which may not hold links or other buttons. Its
body is the card rendered without its own header, so the section's is the only one. A card added
empty starts folded; ``None`` entries are skipped; a dict sets a section's title, menu or folding.
Rendered through both packs: the card around the stack is a pack template, the stack is shared.
"""
import json

from ajax_helpers.mixins import AjaxHelpers
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.utils.html import format_html
from django.views.generic import TemplateView
from django_menus.menu import HtmlMenuItem

from cards import render_scope
from cards.standard import CardMixin, CardSection, build_sections
from cards_examples.tests.test_escaping import ESCAPED_PAYLOAD, PACKS, PAYLOAD, _Page


class _CardView(CardMixin, TemplateView):
    pass


def _view():
    view = _CardView()
    view.request = RequestFactory().get('/')
    return view


def _cards(view):
    contact = view.add_card('contact', title='Contact', menu=[HtmlMenuItem('<b class="contact-menu">Edit</b>')])
    contact.add_entry(value='Brass & Co', label='Company')
    tags = view.add_card('tags', title='Tags', is_empty=True, empty_message='No tags')
    site = view.add_card('site', title='Site')
    site.add_entry(value='Cromer', label='Town')
    return contact, tags, site


class TestAddSections(SimpleTestCase):

    def render(self, entries=None, **card_kwargs):
        view = _view()
        entries = _cards(view) if entries is None else entries(view)
        card = view.add_card('customer', title='Customer', **card_kwargs)
        card.add_sections(entries)
        return card, card.render()

    def test_each_card_is_a_section_with_its_own_title_in_both_packs(self):
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                with self.subTest(pack=pack):
                    _card, html = self.render()
                    page = _Page(html)
                    titles = [a for a in page.find('span') if a.get('class') == 'django-card__section-title']
                    self.assertEqual(len(titles), 3, html)
                    for code in ('contact', 'tags', 'site'):
                        self.assertEqual(len(page.find('div', id=f'{code}-section')), 1, html)
                    self.assertLess(html.index('>Contact<'), html.index('>Tags<'))
                    self.assertLess(html.index('>Tags<'), html.index('>Site<'))
                    # the master card keeps its own header
                    self.assertIn('Customer', html)
                    self.assertIn('cards/css/cards.css', html)

    def test_a_sections_card_draws_no_header_of_its_own(self):
        _card, html = self.render()
        body = html[html.index('id="contact-section-body"'):]
        self.assertNotIn('card-header', body[:body.index('id="tags-section"')])
        self.assertIn('Brass &amp; Co', body)

    def test_the_cards_menu_sits_beside_the_toggle_not_in_it(self):
        _card, html = self.render()
        section = html[html.index('id="contact-section"'):html.index('id="tags-section"')]
        toggle = section[section.index('<button'):section.index('</button>')]
        self.assertNotIn('contact-menu', toggle)
        self.assertIn('django-card__section-menu', section)
        self.assertIn('contact-menu', section)
        self.assertIn('django-card__section-bar--has-menu', section)
        # a section with no menu has no menu slot
        tags = html[html.index('id="tags-section"'):html.index('id="site-section"')]
        self.assertNotIn('django-card__section-menu', tags)

    def test_an_empty_card_starts_folded_and_the_rest_open(self):
        _card, html = self.render()
        page = _Page(html)
        folded = {a['id'] for a in page.find('div') if 'django-card__section--folded' in (a.get('class') or '')}
        self.assertEqual(folded, {'tags-section'})
        expanded = {b.get('aria-controls'): b.get('aria-expanded') for b in page.find('button')
                    if b.get('class') == 'django-card__section-toggle'}
        self.assertEqual(expanded, {'contact-section-body': 'true', 'tags-section-body': 'false',
                                    'site-section-body': 'true'})
        self.assertIn('No tags', html)

    def test_a_dict_sets_title_menu_and_folding_and_none_is_skipped(self):
        def entries(view):
            contact, tags, site = _cards(view)
            return [{'card': contact, 'title': PAYLOAD, 'folded': True},
                    None,
                    {'card': tags, 'folded': False, 'title': format_html('<em class="made">{}</em>', 'Tags')},
                    site]

        _card, html = self.render(entries)
        page = _Page(html)
        self.assertEqual(page.find('img'), [], html)
        self.assertIn(ESCAPED_PAYLOAD, html)
        self.assertEqual(len(page.find('em', **{'class': 'made'})), 1)
        folded = {a['id'] for a in page.find('div') if 'django-card__section--folded' in (a.get('class') or '')}
        self.assertEqual(folded, {'contact-section'})

    def test_the_stack_is_drawn_when_the_card_is_rendered(self):
        """After cards_ready(): a row added to a section's card after add_sections() is drawn."""
        view = _view()
        contact, tags, site = _cards(view)
        card = view.add_card('customer', title='Customer').add_sections([contact])
        contact.add_entry(value='added late', label='Late')
        card.add_sections([site])
        html = card.render()
        self.assertIn('added late', html)
        self.assertIn('id="site-section"', html)

    def test_called_twice_it_adds_to_the_stack(self):
        view = _view()
        contact, tags, site = _cards(view)
        card = view.add_card('customer', title='Customer')
        card.add_sections([contact]).add_sections([tags, site])
        self.assertEqual([s.card.code for s in card.extra_card_info['sections']], ['contact', 'tags', 'site'])

    def test_the_card_becomes_the_sections_and_an_ajax_reload_keeps_it_so(self):
        """Its header is off on the card, so the reload's re-render (`_render_template`, which
        `button_reload_card` answers with) draws it without one too."""
        view = _view()
        contact, _tags, _site = _cards(view)
        view.add_card('customer', title='Customer').add_sections([contact])
        self.assertFalse(contact.show_header)
        self.assertNotIn('card-header', contact._render_template())

    def test_a_collapsed_card_starts_folded_and_its_body_can_be_opened(self):
        view = _view()
        notes = view.add_card('notes', title='Notes', collapsed=True)
        notes.add_entry(value='inside', label='Note')
        html = view.add_card('customer', title='Customer').add_sections([notes]).render()
        page = _Page(html)
        self.assertEqual(len([a for a in page.find('div', id='notes-section')
                              if 'django-card__section--folded' in a.get('class', '')]), 1)
        # the card's own collapse is off: its body is not a .collapse the section cannot open
        body = [a for a in page.find('div', id='notes_body')]
        self.assertEqual(len(body), 1)
        self.assertNotIn('collapse', body[0].get('class', '').split())

    def test_a_reloading_cards_reload_button_moves_to_the_section_header(self):
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                with self.subTest(pack=pack):
                    view = _view()
                    live = view.add_card('live', title='Live', ajax_reload=True)
                    live.add_entry(value='1', label='Count')
                    html = view.add_card('customer', title='Customer').add_sections([live]).render()
                    header = html[html.index('id="live-section"'):html.index('id="live-section-body"')]
                    self.assertIn("reload_card('live')", header)
                    self.assertIn('id="live_ajax"', html)

    def test_a_menu_whose_items_are_all_hidden_reserves_no_room(self):
        class Forbidden(HtmlMenuItem):
            def test_visible(self, request):
                self.visible = False
                return False

        view = _view()
        card = view.add_card('locked', title='Locked', menu=[Forbidden('<b>Edit</b>')])
        card.add_entry(value='x', label='X')
        html = view.add_card('customer', title='Customer').add_sections([card]).render()
        self.assertNotIn('django-card__section-menu', html)
        self.assertNotIn('--has-menu', html)

    def test_a_menu_given_as_a_list_is_drawn(self):
        view = _view()
        contact, _tags, _site = _cards(view)
        html = view.add_card('customer', title='Customer').add_sections(
            [{'card': contact, 'menu': [HtmlMenuItem('<b class="listed">Edit</b>')]}]).render()
        section = html[html.index('id="contact-section"'):html.index('id="contact-section-body"')]
        self.assertIn('class="listed"', section)

    def test_what_is_not_a_section_raises_at_add_sections(self):
        view = _view()
        customer = view.add_card('customer', title='Customer')
        with self.assertRaises(TypeError):
            customer.add_sections(['contact'])
        with self.assertRaisesMessage(ValueError, 'needs its card'):
            customer.add_sections([{'title': 'Contact'}])
        with self.assertRaisesMessage(ValueError, 'has no title'):
            customer.add_sections([view.add_card('untitled')])

    def test_opening_a_section_re_lays_out_datatables_and_says_so(self):
        _card, html = self.render()
        self.assertIn('onclick="djangoCardsToggleSection(this)"', html)
        self.assertIn('columns.adjust()', html)
        self.assertIn("'django-cards:section-toggle'", html)


class TestBuildSectionsInATemplateOfYourOwn(SimpleTestCase):

    def test_the_shared_body_renders_from_a_list_of_sections(self):
        view = _view()
        sections = build_sections([None, *_cards(view)])
        self.assertTrue(all(isinstance(s, CardSection) for s in sections))
        html = render_to_string('cards/standard/_section_stack_body.html', {'sections': sections})
        self.assertEqual(html.count('class="django-card__section-toggle"'), 3)


class _ReloadView(AjaxHelpers, CardMixin, TemplateView):
    """A page whose stack is built in setup_cards, as a reload rebuilds it."""
    title = 'Contact'

    def setup_cards(self):
        contact = self.add_card('contact', title=self.title, ajax_reload=True)
        contact.add_entry(value='Brass & Co', label='Company')
        self.add_card('customer', title='Customer').add_sections([contact])


class TestSectionReviewFixes(SimpleTestCase):

    def test_a_layout_card_in_a_section_draws_no_header_of_its_own(self):
        view = _view()
        group = view.add_layout_card('group')
        group.title = 'Group'
        html = view.add_card('customer', title='Customer').add_sections([group]).render()
        body = html[html.index('id="group-section-body"'):]
        self.assertNotIn('card-header', body)

    def test_the_cards_header_controls_move_to_the_section_header(self):
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                with self.subTest(pack=pack):
                    view = _view()
                    card = view.add_card('rows', title='Rows', searchable=True, exportable=True,
                                         header_icon='fas fa-star', header_css_class='made-header')
                    card.add_entry(value='one', label='First')
                    html = view.add_card('customer', title='Customer').add_sections([card]).render()
                    header = html[html.index('id="rows-section-header"'):html.index('id="rows-section-body"')]
                    self.assertIn('id="rows_search"', header)
                    self.assertIn("exportCard('rows','csv')", header)
                    self.assertIn('fas fa-star', header)
                    self.assertIn('made-header', header)

    def test_the_header_reads_the_card_when_it_is_drawn(self):
        """A title or menu changed after add_sections() -- in cards_ready(), say -- reaches the header."""
        view = _view()
        contact, _tags, _site = _cards(view)
        card = view.add_card('customer', title='Customer').add_sections([contact])
        contact.title = 'Renamed'
        contact.menu = None
        html = card.render()
        header = html[html.index('id="contact-section-header"'):html.index('id="contact-section-body"')]
        self.assertIn('>Renamed<', header)
        self.assertNotIn('contact-menu', header)

    def test_a_reload_redraws_the_section_header_too(self):
        class Renamed(_ReloadView):
            title = 'Contact (2)'

        view = Renamed()
        view.request = RequestFactory().post('/')
        view.setup_cards()
        commands = json.loads(view.button_reload_card(card='contact').content)
        selectors = [c.get('selector') for c in commands]
        self.assertEqual(selectors, ['#contact-section-header', '#contact_ajax'])
        self.assertIn('Contact (2)', commands[0]['html'])
        self.assertNotIn('card-header', commands[1]['html'])

    def test_the_stack_is_drawn_once_however_often_it_is_read(self):
        view = _view()
        contact, _tags, _site = _cards(view)
        card = view.add_card('customer', title='Customer').add_sections([contact])
        calls = []
        original = contact.render
        contact.render = lambda *a, **k: calls.append(1) or original(*a, **k)
        html = card.extra_card_info['html']
        str(html), str(html), bool(html)
        card.render()
        self.assertEqual(len(calls), 1)

    def test_a_bad_entry_leaves_every_card_as_it_was(self):
        view = _view()
        contact, _tags, _site = _cards(view)
        with self.assertRaises(TypeError):
            view.add_card('customer', title='Customer').add_sections([contact, 'oops'])
        self.assertTrue(contact.show_header)
        self.assertFalse(hasattr(contact, 'section'))

    def test_a_card_that_already_has_a_body_refuses_a_stack(self):
        from cards.base import CARD_TYPE_DATATABLE
        from cards_examples.models import Company

        class _TableView(CardMixin, TemplateView):
            def setup_table(self, table, details_object):
                table.ajax_data = True
                table.add_columns('id', 'name')

        view = _view()
        contact, _tags, _site = _cards(view)
        rows = view.add_card('rows', title='Rows')
        rows.add_entry(value='x', label='X')
        table_view = _TableView()
        table_view.request = RequestFactory().get('/')
        table = table_view.add_card('table', title='Table', group_type=CARD_TYPE_DATATABLE, datatable_model=Company)
        for card in (view.add_card('empty', title='Empty', is_empty=True), rows, table):
            with self.subTest(card=card.code):
                with self.assertRaisesMessage(ValueError, 'already has one'):
                    card.add_sections([contact])
        self.assertTrue(contact.show_header)

    def test_opening_a_section_re_lays_out_only_its_own_datatables(self):
        _card, html = TestAddSections().render()
        self.assertIn("$(section).find('table.dataTable')", html)
        self.assertNotIn('tables({visible', html)

    def test_section_ids_cannot_be_another_cards(self):
        view = _view()
        contact, _tags, _site = _cards(view)
        view.add_card('contact-section-body', title='Clash')
        with self.assertRaisesMessage(ValueError, 'contact-section-body'):
            view.add_card('customer', title='Customer').add_sections([contact])
        self.assertTrue(contact.show_header)

    def test_the_toggle_script_comes_once_per_request(self):
        with _Request():
            view = _view()
            a1, _t, _s = _cards(view)
            first = view.add_card('first', title='First').add_sections([a1]).render()
            view2 = _view()
            b1, _t2, _s2 = _cards(view2)
            second = view2.add_card('second', title='Second').add_sections([b1]).render()
        self.assertEqual((first + second).count('window.djangoCardsToggleSection ='), 1)
        # in a template of your own, with no section_script given, it comes with the stack
        view = _view()
        html = render_to_string('cards/standard/_section_stack_body.html', {'sections': build_sections(_cards(view))})
        self.assertIn('window.djangoCardsToggleSection =', html)


class _Request:
    def __enter__(self):
        render_scope._open_scope()

    def __exit__(self, *exc):
        render_scope._close_scope()


class TestTheHeadersHonourShowHeader(SimpleTestCase):
    """card_group, list_selection, tree_selection and image_gallery drew their header whatever
    show_header said, so in a section one was drawn twice. Rendered with a stand-in card, as
    test_tab_menu_rendered does: only the header is under test."""

    TEMPLATES = ('card_group', 'list_selection', 'tree_selection', 'image_gallery')

    def render(self, pack, name, **context):
        from cards_examples.tests.test_tab_menu_rendered import _Card
        card = _Card()
        return render_to_string(f'cards/{pack}/standard/{name}.html', {'card': card, **context})

    def test_show_header_off_draws_none(self):
        for pack in PACKS:
            for name in self.TEMPLATES:
                with self.subTest(pack=pack, template=name):
                    self.assertNotIn('card-header', self.render(pack, name, show_header=False))

    def test_unset_or_on_still_draws_it(self):
        for pack in PACKS:
            for name in self.TEMPLATES:
                with self.subTest(pack=pack, template=name):
                    self.assertIn('card-header', self.render(pack, name))
                    self.assertIn('card-header', self.render(pack, name, show_header=True))
