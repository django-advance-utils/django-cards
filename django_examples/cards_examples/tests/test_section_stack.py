"""``card.add_sections(cards)``: a card whose body is a stack of folding sections, one per card.

Each section's header is a native toggle button holding the card's title and a chevron, with the
card's own menu beside it -- outside the button, which may not hold links or other buttons. Its
body is the card rendered without its own header, so the section's is the only one. A card added
empty starts folded; ``None`` entries are skipped; a dict sets a section's title, menu or folding.
Rendered through both packs: the card around the stack is a pack template, the stack is shared.
"""
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.utils.html import format_html
from django.views.generic import TemplateView
from django_menus.menu import HtmlMenuItem

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
                        self.assertEqual(len(page.find('div', id=f'{code}_section')), 1, html)
                    self.assertLess(html.index('>Contact<'), html.index('>Tags<'))
                    self.assertLess(html.index('>Tags<'), html.index('>Site<'))
                    # the master card keeps its own header
                    self.assertIn('Customer', html)
                    self.assertIn('cards/css/cards.css', html)

    def test_a_sections_card_draws_no_header_of_its_own(self):
        _card, html = self.render()
        body = html[html.index('id="contact_section_body"'):]
        self.assertNotIn('card-header', body[:body.index('id="tags_section"')])
        self.assertIn('Brass &amp; Co', body)

    def test_the_cards_menu_sits_beside_the_toggle_not_in_it(self):
        _card, html = self.render()
        section = html[html.index('id="contact_section"'):html.index('id="tags_section"')]
        toggle = section[section.index('<button'):section.index('</button>')]
        self.assertNotIn('contact-menu', toggle)
        self.assertIn('django-card__section-menu', section)
        self.assertIn('contact-menu', section)
        self.assertIn('django-card__section-header--has-menu', section)
        # a section with no menu has no menu slot
        tags = html[html.index('id="tags_section"'):html.index('id="site_section"')]
        self.assertNotIn('django-card__section-menu', tags)

    def test_an_empty_card_starts_folded_and_the_rest_open(self):
        _card, html = self.render()
        page = _Page(html)
        folded = {a['id'] for a in page.find('div') if 'django-card__section--folded' in (a.get('class') or '')}
        self.assertEqual(folded, {'tags_section'})
        expanded = {b.get('aria-controls'): b.get('aria-expanded') for b in page.find('button')
                    if b.get('class') == 'django-card__section-toggle'}
        self.assertEqual(expanded, {'contact_section_body': 'true', 'tags_section_body': 'false',
                                    'site_section_body': 'true'})
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
        self.assertEqual(folded, {'contact_section'})

    def test_the_stack_is_drawn_when_the_card_is_rendered(self):
        """After cards_ready(): a row added to a section's card after add_sections() is drawn."""
        view = _view()
        contact, tags, site = _cards(view)
        card = view.add_card('customer', title='Customer').add_sections([contact])
        contact.add_entry(value='added late', label='Late')
        card.add_sections([site])
        html = card.render()
        self.assertIn('added late', html)
        self.assertIn('id="site_section"', html)

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
        self.assertEqual(len([a for a in page.find('div', id='notes_section')
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
                    header = html[html.index('id="live_section"'):html.index('id="live_section_body"')]
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
        section = html[html.index('id="contact_section"'):html.index('id="contact_section_body"')]
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
