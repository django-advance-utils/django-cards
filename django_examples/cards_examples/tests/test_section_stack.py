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

    def test_called_twice_it_adds_to_the_stack(self):
        view = _view()
        contact, tags, site = _cards(view)
        card = view.add_card('customer', title='Customer')
        card.add_sections([contact]).add_sections([tags, site])
        self.assertEqual([s.card.code for s in card.extra_card_info['sections']], ['contact', 'tags', 'site'])

    def test_the_section_card_is_not_changed(self):
        """Its header is switched off for this render, not on the card, which may be shown elsewhere."""
        view = _view()
        contact, _tags, _site = _cards(view)
        view.add_card('customer', title='Customer').add_sections([contact]).render()
        self.assertTrue(contact.show_header)
        self.assertIn('card-header', contact.render())


class TestBuildSectionsInATemplateOfYourOwn(SimpleTestCase):

    def test_the_shared_body_renders_from_a_list_of_sections(self):
        view = _view()
        sections = build_sections([None, *_cards(view)])
        self.assertTrue(all(isinstance(s, CardSection) for s in sections))
        html = render_to_string('cards/standard/_section_stack_body.html', {'sections': sections})
        self.assertEqual(html.count('class="django-card__section-toggle"'), 3)
