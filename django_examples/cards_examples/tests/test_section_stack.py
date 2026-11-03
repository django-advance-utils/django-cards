"""``card.add_sections(cards)``: a card whose body is a stack of folding sections, one per card.

Each section's header is a native toggle naming the section (the card's title), the card's own
header controls beside it -- outside the button, which may not hold links or other buttons -- and a
chevron. Its body is the card drawn without its own header, for that render only: the card itself is
not changed. A card added empty starts folded; ``None`` entries are skipped; a dict sets a section's
title, menu or folding.

A card is in one place on a page, stacked once in the build that made it: the view keeps this
build's stacks (``SECTION_STACKS``), which ``build_cards()`` starts again, and checks every new
section against them. An ajax reload of a section's card finds its section in the rebuilt stacks.
"""
import json
import pathlib

from ajax_helpers.mixins import AjaxHelpers
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.utils.html import escapejs, format_html
from django.views.generic import TemplateView
from django_menus.menu import HtmlMenuItem

from cards import render_scope
from cards.base import CARD_TYPE_DATATABLE, BannerTile, CardBase, Tile, find_section
from cards.standard import CardMixin, CardSection, build_sections
from cards_examples.models import Company
from cards_examples.tests.test_escaping import ESCAPED_PAYLOAD, PACKS, PAYLOAD, _Page


class _CardView(CardMixin, TemplateView):
    def setup_table(self, table, details_object):
        table.ajax_data = True
        table.add_columns('id', 'name')


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


def _stack(entries=None, **card_kwargs):
    view = _view()
    entries = _cards(view) if entries is None else entries(view)
    card = view.add_card('customer', title='Customer', **card_kwargs).add_sections(entries)
    return view, card, card.render()


def _between(html, start, end):
    return html[html.index(start):html.index(end)]


def _folded(html):
    return {a['id'] for a in _Page(html).find('div') if 'django-card__section--folded' in (a.get('class') or '')}


class _Request:
    """One request cycle's render scope, as django's request signals open and close it."""

    def __enter__(self):
        render_scope._open_scope()

    def __exit__(self, *exc):
        render_scope._close_scope()


class TestTheStack(SimpleTestCase):

    def test_each_card_is_a_section_with_its_own_title_in_both_packs(self):
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                with self.subTest(pack=pack):
                    _view_, _card, html = _stack()
                    page = _Page(html)
                    titles = [a for a in page.find('span') if a.get('class') == 'django-card__section-title']
                    self.assertEqual(len(titles), 3, html)
                    for code in ('contact', 'tags', 'site'):
                        self.assertEqual(len(page.find('div', id=f'{code}-section')), 1, html)
                    self.assertLess(html.index('>Contact<'), html.index('>Tags<'))
                    self.assertLess(html.index('>Tags<'), html.index('>Site<'))
                    self.assertIn('Customer', html)  # the stack card keeps its own header
                    self.assertIn('cards/css/cards.css', html)

    def test_a_section_draws_its_card_without_the_cards_header_and_leaves_the_card_as_it_was(self):
        view, _card, html = _stack()
        body = _between(html, 'id="contact-section-body"', 'id="tags-section"')
        self.assertNotIn('card-header', body)
        self.assertIn('Brass &amp; Co', body)
        contact = view.cards['contact']
        self.assertTrue(contact.show_header)

    def test_the_cards_menu_sits_beside_the_toggle_not_in_it(self):
        _view_, _card, html = _stack()
        section = _between(html, 'id="contact-section"', 'id="tags-section"')
        toggle = section[section.index('<button'):section.index('</button>')]
        self.assertNotIn('contact-menu', toggle)
        self.assertIn('django-card__section-menu', section)
        self.assertIn('contact-menu', section)
        self.assertNotIn('django-card__section-menu', _between(html, 'id="tags-section"', 'id="site-section"'))

    def test_the_header_is_a_row_title_controls_then_chevron(self):
        _view_, _card, html = _stack()
        header = _between(html, 'id="contact-section-header"', 'id="contact-section-body"')
        self.assertLess(header.index('class="django-card__section-toggle"'), header.index('class="django-card__section-menu"'))
        self.assertLess(header.index('class="django-card__section-menu"'), header.index('class="django-card__section-chevron-button"'))
        # the chevron is decorative -- no hidden button -- and a click on the bar's free space
        # toggles; the toggle is the one control a keyboard or screen reader meets
        self.assertEqual([b for b in _Page(header).find('button') if 'chevron' in (b.get('class') or '')], [])
        chevron = [a for a in _Page(header).find('span') if a.get('class') == 'django-card__section-chevron-button'][0]
        self.assertEqual(chevron.get('aria-hidden'), 'true')
        bar = [a for a in _Page(header).find('div') if (a.get('class') or '').startswith('django-card__section-bar')][0]
        self.assertEqual(bar.get('onclick'), 'djangoCardsSectionBarClick(event)')

    def test_an_empty_card_starts_folded_and_the_rest_open(self):
        _view_, _card, html = _stack()
        self.assertEqual(_folded(html), {'tags-section'})
        expanded = {b.get('aria-controls'): b.get('aria-expanded') for b in _Page(html).find('button')
                    if b.get('class') == 'django-card__section-toggle'}
        self.assertEqual(expanded, {'contact-section-body': 'true', 'tags-section-body': 'false',
                                    'site-section-body': 'true'})

    def test_a_dict_sets_title_menu_and_folding_and_none_is_skipped(self):
        def entries(view):
            contact, tags, site = _cards(view)
            return [{'card': contact, 'title': PAYLOAD, 'folded': True,
                     'menu': [HtmlMenuItem('<b class="listed">Edit</b>')]},
                    None,
                    {'card': tags, 'folded': False, 'title': format_html('<em class="made">{}</em>', 'Tags')},
                    site]

        _view_, _card, html = _stack(entries)
        page = _Page(html)
        self.assertEqual(page.find('img'), [], html)
        self.assertIn(ESCAPED_PAYLOAD, html)
        self.assertEqual(len(page.find('em', **{'class': 'made'})), 1)
        self.assertEqual(_folded(html), {'contact-section'})
        self.assertIn('class="listed"', _between(html, 'id="contact-section"', 'id="contact-section-body"'))

    def test_called_twice_it_adds_to_the_stack(self):
        view = _view()
        contact, tags, site = _cards(view)
        card = view.add_card('customer', title='Customer').add_sections([contact]).add_sections([tags, site])
        self.assertEqual([s.card.code for s in card.extra_card_info['sections']], ['contact', 'tags', 'site'])

    def test_the_header_and_body_read_the_card_when_they_are_drawn(self):
        """After cards_ready(): a title, menu or row changed after add_sections() is drawn."""
        view = _view()
        contact, _tags, _site = _cards(view)
        late = view.add_card('late')
        late.add_entry(value='x', label='X')
        card = view.add_card('customer', title='Customer').add_sections([contact, late])
        contact.title = 'Renamed'
        contact.menu = None
        contact.add_entry(value='added late', label='Late')
        late.title = 'Set in cards_ready'
        html = card.render()
        header = _between(html, 'id="contact-section-header"', 'id="contact-section-body"')
        self.assertIn('>Renamed<', header)
        self.assertNotIn('contact-menu', header)
        self.assertIn('added late', html)
        self.assertIn('>Set in cards_ready<', html)

    def test_a_section_with_no_title_raises_when_it_is_drawn(self):
        view = _view()
        card = view.add_card('customer', title='Customer').add_sections([view.add_card('untitled')])
        with self.assertRaisesMessage(ValueError, 'has no title'):
            card.render()

    def test_the_stack_is_drawn_once_however_often_it_is_read(self):
        view = _view()
        contact, _tags, _site = _cards(view)
        card = view.add_card('customer', title='Customer').add_sections([contact])
        calls = []
        original = contact.render
        contact.render = lambda *a, **k: calls.append(1) or original(*a, **k)
        read = card.extra_card_info['html']
        read(), read()
        card.render()
        self.assertEqual(len(calls), 1)

    def test_a_subclass_with_templates_of_its_own_can_hold_a_stack(self):
        """JMSCard-style: a subclass whose templates list neither a stack nor the controls flag."""
        class OwnTemplates(CardBase):
            templates = {'default': {'name': 'cards/standard/default.html',
                                     'context': {'card_css_class': 'card mine'}},
                         'html': {'name': 'cards/standard/html.html',
                                  'context': {'card_css_class': 'card mine'}}}

        class View(CardMixin, TemplateView):
            card_cls = OwnTemplates

        view = View()
        view.request = RequestFactory().get('/')
        rows = view.add_card('rows', title='Rows', searchable=True)
        rows.add_entry(value='one', label='First')
        html = view.add_card('customer', title='Customer').add_sections([rows]).render()
        self.assertIn('id="rows-section"', html)
        self.assertIn('id="rows_search"', _between(html, 'id="rows-section-header"', 'id="rows-section-body"'))


class TestTheHeadersControls(SimpleTestCase):

    def test_search_export_icon_and_class_reach_the_section_header(self):
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                with self.subTest(pack=pack):
                    def entries(view):
                        card = view.add_card('rows', title='Rows', searchable=True, exportable=True,
                                             header_icon='fas fa-star', header_css_class='made-header')
                        card.add_entry(value='one', label='First')
                        return [card]

                    _view_, _card, html = _stack(entries)
                    header = _between(html, 'id="rows-section-header"', 'id="rows-section-body"')
                    self.assertIn('id="rows_search"', header)
                    self.assertIn("exportCard('rows','csv')", header)
                    self.assertIn('fas fa-star', header)
                    self.assertIn('made-header', header)

    def test_search_and_export_only_where_the_cards_template_has_their_scripts(self):
        def entries(view):
            notes = view.add_html_data_card(card_name='notes', title='Notes', html='<p>n</p>',
                                            searchable=True, exportable=True, ajax_reload=True)
            plain = view.add_html_data_card(card_name='plain', title='Plain', html='<p>p</p>', searchable=True)
            plain.section_header_controls = True  # its template carries them some other way
            return [notes, plain]

        _view_, _card, html = _stack(entries)
        notes = _between(html, 'id="notes-section-header"', 'id="notes-section-body"')
        self.assertNotIn('notes_search', notes)
        self.assertNotIn('exportCard', notes)
        self.assertIn("reload_card('notes')", notes)
        self.assertIn('id="plain_search"', _between(html, 'id="plain-section-header"', 'id="plain-section-body"'))

    def test_the_card_templates_and_the_section_share_their_header_controls(self):
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                for template_name in ('default', 'table'):
                    with self.subTest(pack=pack, template=template_name):
                        card = _view().add_card('rows', title='Rows', template_name=template_name,
                                                searchable=True, exportable=True, ajax_reload=True)
                        card.add_entry(value='one', label='First')
                        html = card.render()
                        self.assertIn('id="rows_search"', html)
                        self.assertIn("exportCard('rows','csv')", html)
                        self.assertIn("reload_card('rows')", html)

    def test_a_menu_whose_items_are_all_hidden_reserves_no_room(self):
        from django_menus.menu import HtmlMenu, MenuItem

        class Forbidden(HtmlMenuItem):
            def test_visible(self, request):
                self.visible = False
                return False

        def entries(view):
            locked = view.add_card('locked', title='Locked', menu=[Forbidden('<b>Edit</b>')])
            locked.add_entry(value='x', label='X')
            menu = HtmlMenu(view.request, 'button_group').add_items(
                MenuItem('cards_examples:hello_modal', menu_display='Edit', visible=False))
            self.assertEqual(menu.render(), '')  # what the header relies on
            hidden = view.add_card('hidden', title='Hidden', menu=menu)
            hidden.add_entry(value='x', label='X')
            return [locked, hidden]

        _view_, _card, html = _stack(entries)
        self.assertNotIn('class="django-card__section-menu"', html)

    def test_a_menus_items_are_asked_once_per_header(self):
        asked = []

        class Counted(HtmlMenuItem):
            def test_visible(self, request):
                asked.append(1)
                return super().test_visible(request)

        view = _view()
        card = view.add_card('counted', title='Counted', menu=[Counted('<b>Edit</b>')])
        card.add_entry(value='x', label='X')
        stack = view.add_card('customer', title='Customer').add_sections([card])
        asked.clear()
        stack.render()
        self.assertEqual(len(asked), 1)

    def test_a_header_class_colours_the_title(self):
        css = (pathlib.Path(__file__).resolve().parents[3] / 'cards/static/cards/css/cards.css').read_text()
        bar = css[css.index('.django-card__section-bar {'):]
        self.assertIn('color: var(--django-card-section-title-color', bar[:bar.index('}')])
        toggle = css[css.index('.django-card__section-toggle,\n.django-card__section-chevron-button {'):]
        self.assertIn('color: inherit;', toggle[:toggle.index('}')])


class TestWhatAStackRefuses(SimpleTestCase):

    def test_what_is_not_a_section_raises(self):
        view = _view()
        customer = view.add_card('customer', title='Customer')
        with self.assertRaises(TypeError):
            customer.add_sections(['contact'])
        with self.assertRaisesMessage(ValueError, 'needs its card'):
            customer.add_sections([{'title': 'Contact'}])

    def test_a_card_built_collapsed_raises(self):
        view = _view()
        for collapsed in (True, False):
            with self.subTest(collapsed=collapsed):
                notes = view.add_card(f'notes_{collapsed}', title='Notes', collapsed=collapsed)
                with self.assertRaisesMessage(ValueError, 'the section is its fold'):
                    view.add_card(f'customer_{collapsed}', title='Customer').add_sections([notes])

    def test_a_stack_cannot_hold_itself(self):
        view = _view()
        a = view.add_card('a', title='A')
        b = view.add_card('b', title='B')
        with self.assertRaisesMessage(ValueError, 'holds itself'):
            a.add_sections([a])
        b.add_sections([view.add_card('leaf', title='Leaf')])
        a.add_sections([b])
        with self.assertRaisesMessage(ValueError, 'holds itself'):
            b.add_sections([a])

    def test_a_cycle_made_another_way_fails_cleanly_not_by_recursion(self):
        view = _view()
        a = view.add_card('a', title='A').add_sections([view.add_card('leaf', title='Leaf')])
        a.extra_card_info['sections'].append(CardSection(a))
        with self.assertRaisesMessage(ValueError, 'contains itself'):
            a.render()

    def test_a_card_is_in_one_stack_once_named_or_not(self):
        view = _view()
        contact, _tags, site = _cards(view)
        with self.assertRaisesMessage(ValueError, 'in a section stack already'):
            view.add_card('one', title='One').add_sections([contact, contact])
        stack = view.add_card(title='Unnamed').add_sections([contact])
        for again in (lambda: stack.add_sections([contact, site]),
                      lambda: view.add_card('three', title='Three').add_sections([contact]),
                      lambda: view.add_card(title='Also unnamed').add_sections([contact])):
            with self.assertRaisesMessage(ValueError, 'in a section stack already'):
                again()

    def test_two_cards_sharing_a_code_cannot_both_be_sections(self):
        view = _view()
        first = view.add_card(title='Notes')
        second = view.add_card(title='Notes')
        self.assertEqual(first.code, second.code)
        with self.assertRaisesMessage(ValueError, 'share the code'):
            view.add_card('one', title='One').add_sections([first, second])
        view.add_card('two', title='Two').add_sections([first])
        with self.assertRaisesMessage(ValueError, 'share the code'):
            view.add_card('three', title='Three').add_sections([second])

    def test_ids_another_card_or_table_has_raise_and_again_at_render(self):
        class _Table:
            table_id = 'tags-section-body'

        view = _view()
        contact, tags, site = _cards(view)
        for name, card in (('contact-section-toggle', contact), ('customer-sections', site)):
            with self.subTest(name=name):
                view.add_card(name, title='Clash')
                with self.assertRaisesMessage(ValueError, name):
                    view.add_card('customer', title='Customer').add_sections([card])
        view.tables['listing'] = _Table()
        with self.assertRaisesMessage(ValueError, 'tags-section-body'):
            view.add_card('other', title='Other').add_sections([tags])
        late = _view()
        late_card = late.add_card('late_card', title='Late')
        late_card.add_entry(value='x', label='X')
        stack = late.add_card('stack', title='Stack').add_sections([late_card])
        late.add_card('late_card-section-body', title='Added later')
        with self.assertRaisesMessage(ValueError, 'late_card-section-body'):
            stack.render()

    def test_a_card_with_another_body_refuses_a_stack(self):
        view = _view()
        contact, _tags, _site = _cards(view)
        rows = view.add_card('rows', title='Rows')
        rows.add_entry(value='x', label='X')
        table = view.add_card('table', title='Table', group_type=CARD_TYPE_DATATABLE, datatable_model=Company)
        refused = (view.add_card('empty', title='Empty', is_empty=True), rows, table,
                   view.add_card('tiles', title='Tiles').add_tiles([Tile(key='t1', heading='One')]),
                   view.add_card('banners', title='Banners').add_banner_tiles([BannerTile(key='b1', title='One')]),
                   view.add_card('templated', title='Templated', template_name='table'))
        for card in refused:
            with self.subTest(card=card.code):
                with self.assertRaisesMessage(ValueError, 'already has one'):
                    card.add_sections([contact])
        # nothing was recorded: contact can still go into a stack
        view.add_card('customer', title='Customer').add_sections([contact])

    def test_another_body_after_the_stack_raises(self):
        view = _view()
        contact, _tags, _site = _cards(view)
        stack = view.add_card('customer', title='Customer').add_sections([contact])
        for add in (lambda: stack.add_tiles([Tile(key='t1', heading='One')]),
                    lambda: stack.add_banner_tiles([BannerTile(key='b1', title='One')]),
                    lambda: stack.add_entry(value='lost', label='Row'),
                    lambda: stack.add_rows({'label': 'Lost', 'value': 'x'}),
                    lambda: stack.add_html_string_entry('<p>lost</p>')):
            with self.assertRaisesMessage(ValueError, 'holds a section stack'):
                add()

    def test_a_bad_entry_records_nothing(self):
        view = _view()
        contact, _tags, _site = _cards(view)
        with self.assertRaises(TypeError):
            view.add_card('one', title='One').add_sections([contact, 'oops'])
        view.add_card('two', title='Two').add_sections([contact])


class TestBuilds(SimpleTestCase):

    def test_building_the_cards_again_starts_the_stacks_again(self):
        class View(CardMixin, TemplateView):
            def setup_cards(self):
                contact = self.add_card('contact', title='Contact')
                contact.add_entry(value='x', label='X')
                self.add_card('customer', title='Customer').add_sections([contact])

        view = View()
        view.request = RequestFactory().get('/')
        view.build_cards()
        view.build_cards()  # a handler built them, then get_context_data does
        view.rebuild_cards()
        self.assertIs(find_section(view, view.cards['contact']).card, view.cards['contact'])


class _ReloadView(AjaxHelpers, CardMixin, TemplateView):
    title = 'Contact'
    reloads = True

    def setup_cards(self):
        contact = self.add_card('contact', title=self.title, ajax_reload=self.reloads)
        contact.add_entry(value='Brass & Co', label='Company')
        self.add_card('customer', title='Customer').add_sections([contact])


def _reload(view_cls):
    view = view_cls()
    view.request = RequestFactory().post('/')
    view.build_cards()
    return json.loads(view.button_reload_card(card='contact').content)


class TestReload(SimpleTestCase):

    def test_a_reload_redraws_the_section_header_and_the_card_without_its_header(self):
        class Renamed(_ReloadView):
            title = 'Contact (2)'

        commands = _reload(Renamed)
        # the header first, so the body's scripts bind to its new controls; the body, carrying the
        # fold script, after it, so a section it opens re-measures the new body
        self.assertEqual([c.get('selector') for c in commands], ['#contact-section-header', '#contact-section-body'])
        self.assertIn('Contact (2)', commands[0]['html'])
        self.assertNotIn('djangoCardsApplySectionFolds', commands[0]['html'])
        body = commands[1]['html']
        self.assertNotIn('card-header', body)
        self.assertIn('Brass &amp; Co', body)
        self.assertIn('id="contact_ajax"', body)
        self.assertLess(body.index('Brass &amp; Co'), body.index('djangoCardsApplySectionFolds'))

    def test_a_card_that_does_not_reload_is_redrawn_into_its_section_body(self):
        class Plain(_ReloadView):
            reloads = False

        commands = _reload(Plain)
        self.assertEqual([c.get('selector') for c in commands], ['#contact-section-header', '#contact-section-body'])
        self.assertNotIn('card-header', commands[1]['html'])

    def test_a_reload_re_checks_the_sections_ids(self):
        class Late(_ReloadView):
            def cards_ready(self):
                self.add_card('contact-section-body', title='Added late')

        with self.assertRaisesMessage(ValueError, 'contact-section-body'):
            _reload(Late)


class TestAStackOfYourOwn(SimpleTestCase):

    def test_build_sections_draws_with_its_stylesheet_script_and_an_id_of_its_own(self):
        view = _view()
        sections = build_sections(_cards(view))
        self.assertTrue(all(isinstance(s, CardSection) for s in sections))
        html = render_to_string('cards/standard/_section_stack_body.html', {'sections': sections, 'request': view.request})
        self.assertEqual(html.count('class="django-card__section-toggle"'), 3)
        self.assertIn('cards/css/cards.css', html)
        self.assertIn('window.djangoCardsToggleSection =', html)
        self.assertIn('id="contact-section-stack"', html)

    def test_build_sections_checks_as_add_sections_does(self):
        view = _view()
        contact, _tags, site = _cards(view)
        with self.assertRaisesMessage(ValueError, 'in a section stack already'):
            build_sections([contact, contact])
        build_sections([contact])
        with self.assertRaisesMessage(ValueError, 'in a section stack already'):
            view.add_card('customer', title='Customer').add_sections([contact])
        view.add_card('site-section-stack', title='Clash')
        with self.assertRaisesMessage(ValueError, 'site-section-stack'):
            build_sections([site])

    def test_an_empty_stack_draws_nothing(self):
        html = render_to_string('cards/standard/_section_stack_body.html', {'sections': [], 'request': _view().request})
        self.assertNotIn('django-card__sections', html)


class TestTheScript(SimpleTestCase):

    def test_it_comes_once_per_request_on_every_path(self):
        with _Request():
            view = _view()
            first = view.add_card('first', title='First').add_sections([_cards(view)[0]]).render()
            other = _view()
            own = render_to_string('cards/standard/_section_stack_body.html',
                                   {'sections': build_sections(_cards(other)), 'request': other.request})
        self.assertEqual((first + own).count('window.djangoCardsToggleSection ='), 1)

    def test_its_mark_is_set_only_once_it_has_rendered(self):
        from cards.render_scope import emit_once

        class Holder:
            pass

        holder = Holder()

        def broken():
            raise RuntimeError('override')

        for _ in range(2):
            with self.assertRaises(RuntimeError):
                emit_once('_mark', holder, broken)
        self.assertEqual(emit_once('_mark', holder, lambda: 'x'), 'x')
        self.assertEqual(emit_once('_mark', holder, lambda: 'x'), '')

    def test_folding_opening_and_putting_folds_back(self):
        script = render_to_string('cards/standard/_section_stack_script.html')
        # a click: remembered, re-lays out its own visible datatables, says so
        self.assertIn('window.djangoCardsSectionFolds[section.id] = folded', script)
        self.assertIn("parentsUntil(section, '.django-card__section--folded')", script)
        self.assertIn("'django-cards:section-toggle'", script)
        # a fold put back after a redraw does what opening does; a redraw takes the server's fold
        # where the reader chose none
        self.assertIn('if (was !== folded) { window.djangoCardsSectionFolded(section, folded); }', script)
        self.assertIn('serverFolded !== undefined ? serverFolded', script)

    def test_one_inline_call_per_stack_waiting_for_the_script(self):
        view, _card, html = _stack()
        call = 'window.djangoCardsApplySectionFolds && djangoCardsApplySectionFolds('
        self.assertEqual(html.count(call), 1)
        self.assertIn(f"getElementById('{escapejs('customer-sections')}')", html)
        redraw = find_section(view, view.cards['tags']).render_body(redraw=True)
        self.assertIn(call, redraw)
        self.assertIn(f"getElementById('{escapejs('tags-section')}'), true)", redraw)


class TestTheHeadersHonourShowHeader(SimpleTestCase):
    """card_group, list_selection, tree_selection and image_gallery drew their header whatever
    show_header said; now they read it as every other card template does."""

    TEMPLATES = ('card_group', 'list_selection', 'tree_selection', 'image_gallery')

    def render(self, pack, name, **context):
        from cards_examples.tests.test_tab_menu_rendered import _Card
        return render_to_string(f'cards/{pack}/standard/{name}.html', {'card': _Card(), **context})

    def test_off_draws_none_and_on_draws_it(self):
        for pack in PACKS:
            for name in self.TEMPLATES:
                with self.subTest(pack=pack, template=name):
                    self.assertNotIn('card-header', self.render(pack, name, show_header=False))
                    self.assertIn('card-header', self.render(pack, name, show_header=True))

    def test_a_layout_card_in_a_section_draws_no_header_of_its_own(self):
        view = _view()
        group = view.add_layout_card('group')
        group.title = 'Group'
        html = view.add_card('customer', title='Customer').add_sections([group]).render()
        self.assertNotIn('card-header', html[html.index('id="group-section-body"'):])


class TestReviewNineFixes(SimpleTestCase):

    def test_controls_follow_the_template_that_renders(self):
        class OwnDefault(CardBase):
            templates = {**CardBase.templates,
                         'default': {'name': 'cards/standard/html.html', 'context': {}}}

        class View(CardMixin, TemplateView):
            card_cls = OwnDefault

        view = View()
        view.request = RequestFactory().get('/')
        own = view.add_card('own', title='Own', searchable=True, exportable=True)
        own.add_entry(value='x', label='X')
        by_path = view.add_card('by_path', title='By path', template_name='cards/standard/table.html', searchable=True)
        by_path.add_entry(value='x', label='X')
        html = view.add_card('customer', title='Customer').add_sections([own, by_path]).render()
        own_header = _between(html, 'id="own-section-header"', 'id="own-section-body"')
        self.assertNotIn('own_search', own_header)
        self.assertNotIn('exportCard', own_header)
        self.assertIn('id="by_path_search"', _between(html, 'id="by_path-section-header"', 'id="by_path-section-body"'))

    def test_a_stacked_card_cannot_also_be_in_a_card_group(self):
        view = _view()
        contact, _tags, site = _cards(view)
        view.add_card('customer', title='Customer').add_sections([contact, site])
        with self.assertRaisesMessage(ValueError, 'is in a section stack'):
            view.add_card_group(contact)
        with self.assertRaisesMessage(ValueError, 'is in a section stack'):
            view.add_card_group('site')

    def test_starting_the_cards_again_by_any_route_starts_the_stacks_again(self):
        view = _view()
        contact, _tags, _site = _cards(view)
        view.add_card('customer', title='Customer').add_sections([contact])
        view.cards = {}  # a handler of its own, not build_cards()
        again, _t, _s = _cards(view)
        view.add_card('customer', title='Customer').add_sections([again])
        self.assertIs(find_section(view, again).card, again)

    def test_a_dict_with_a_key_it_does_not_take_says_so(self):
        view = _view()
        contact, _tags, _site = _cards(view)
        with self.assertRaisesMessage(ValueError, "['fold']"):
            view.add_card('customer', title='Customer').add_sections([{'card': contact, 'fold': True}])

    def test_string_if_invalid_does_not_become_a_stacks_id(self):
        from django.template import engines
        engine = engines['django'].engine
        before = engine.string_if_invalid
        engine.string_if_invalid = 'INVALID'
        try:
            view = _view()
            html = render_to_string('cards/standard/_section_stack_body.html',
                                    {'sections': build_sections(_cards(view)), 'request': view.request})
        finally:
            engine.string_if_invalid = before
        self.assertIn('id="contact-section-stack"', html)
        self.assertNotIn('id="INVALID"', html)

    def test_a_table_added_after_the_stack_raises_when_drawn(self):
        view = _view()
        contact, _tags, _site = _cards(view)
        stack = view.add_card('customer', title='Customer').add_sections([contact])
        stack.extra_card_info['datatable'] = object()  # as add_table() leaves it
        with self.assertRaisesMessage(ValueError, 'a table or tiles'):
            stack.render()

    def test_one_renderer_serves_every_add_sections_call(self):
        view = _view()
        contact, tags, site = _cards(view)
        card = view.add_card('customer', title='Customer').add_sections([contact])
        first = card.extra_card_info['html']
        card.add_sections([tags, site])
        self.assertEqual(card.extra_card_info['html'], first)
        self.assertIn('id="site-section"', card.render())


class TestReviewTenFixes(SimpleTestCase):

    def test_a_card_in_a_card_group_or_layout_first_cannot_be_stacked(self):
        view = _view()
        contact, _tags, site = _cards(view)
        view.add_card_group('contact')
        with self.assertRaisesMessage(ValueError, 'placed on the page already'):
            view.add_card('customer', title='Customer').add_sections([contact])
        layout = view.add_layout_card('layout')
        layout.add_child_card_group(site)
        with self.assertRaisesMessage(ValueError, 'placed on the page already'):
            view.add_card('other', title='Other').add_sections([site])

    def test_a_card_class_without_the_html_template_says_so_up_front(self):
        class NoHtml(CardBase):
            templates = {'default': CardBase.templates['default']}

        class View(CardMixin, TemplateView):
            card_cls = NoHtml

        view = View()
        view.request = RequestFactory().get('/')
        contact = view.add_card('contact', title='Contact')
        with self.assertRaisesMessage(ValueError, "no 'html' entry"):
            view.add_card('customer', title='Customer').add_sections([contact])

    def test_a_pages_own_stack_id_does_not_become_a_stacks(self):
        view = _view()
        html = render_to_string('cards/standard/_section_stack_body.html',
                                {'sections': build_sections(_cards(view)), 'request': view.request,
                                 'stack_id': 'sidebar'})
        self.assertIn('id="contact-section-stack"', html)
        self.assertNotIn('id="sidebar"', html)

    def test_a_table_already_added_is_refused_up_front(self):
        view = _view()
        contact, _tags, _site = _cards(view)
        card = view.add_card('customer', title='Customer')
        card.extra_card_info['datatable'] = object()  # as add_table() leaves it
        with self.assertRaisesMessage(ValueError, 'already has one'):
            card.add_sections([contact])

    def test_something_card_shaped_that_is_not_a_card_is_a_type_error(self):
        class Lookalike:
            code = 'x'

            def render(self):
                return ''

        with self.assertRaises(TypeError):
            _view().add_card('customer', title='Customer').add_sections([Lookalike()])


class TestReviewElevenFixes(SimpleTestCase):

    def test_a_stacked_card_cannot_go_into_a_layouts_child_group(self):
        view = _view()
        contact, _tags, _site = _cards(view)
        view.add_card('customer', title='Customer').add_sections([contact])
        with self.assertRaisesMessage(ValueError, 'is in a section stack'):
            view.add_layout_card('layout').add_child_card_group(contact)

    def test_the_header_controls_sit_in_a_block_so_the_export_dropdown_is_valid(self):
        def entries(view):
            card = view.add_card('rows', title='Rows', exportable=True)
            card.add_entry(value='x', label='X')
            return [card]

        _view_, _card, html = _stack(entries)
        self.assertIn('<div class="django-card__section-menu">', html)
        self.assertNotIn('<span class="django-card__section-menu">', html)

    def test_a_body_class_the_caller_chose_is_kept(self):
        view = _view()
        contact, _tags, _site = _cards(view)
        card = view.add_card('customer', title='Customer', extra_card_context={'card_body_css_class': 'card-body bg-light'})
        card.add_sections([contact])
        self.assertIn('card-body bg-light', card.render())


class TestFollowUp(SimpleTestCase):

    def test_a_card_in_a_panel_layout_region_or_tab_and_a_stack_raises_either_way(self):
        view = _view()
        contact, tags, _site = _cards(view)
        layout = view.add_panel_layout(card_name='shell', persist=False)
        layout.root.add_region('side', size='240px').add_card(contact)
        layout.root.add_region('main', size='1fr').add_tab('one', title='One').add_card(tags)
        for card in (contact, tags):
            with self.subTest(card=card.code):
                with self.assertRaisesMessage(ValueError, 'placed on the page already'):
                    view.add_card(f'stack_{card.code}', title='Stack').add_sections([card])
        other = _view()
        stacked, _t, _s = _cards(other)
        other.add_card('customer', title='Customer').add_sections([stacked])
        later = other.add_panel_layout(card_name='later', persist=False)
        later.root.add_region('main', size='1fr').add_card(stacked)
        with self.assertRaisesMessage(ValueError, 'a panel layout region'):
            str(later.render().render())

    def test_a_card_in_an_accordion_panel_and_a_stack_raises_either_way(self):
        view = _view()
        contact, _tags, site = _cards(view)
        view.add_accordion_card(card_name='acc', title='Acc', panels=[{'title': 'Contact', 'card': contact}])
        with self.assertRaisesMessage(ValueError, 'placed on the page already'):
            view.add_card('customer', title='Customer').add_sections([contact])
        view.add_card('other', title='Other').add_sections([site])
        with self.assertRaisesMessage(ValueError, 'an accordion panel'):
            view.add_accordion_card(card_name='acc2', title='Acc 2', panels=[{'title': 'Site', 'card': site}])

    def test_a_stack_of_your_own_re_checks_its_ids_when_it_renders(self):
        view = _view()
        sections = build_sections(_cards(view))
        view.add_card('contact-section-body', title='Added later')
        with self.assertRaisesMessage(ValueError, 'contact-section-body'):
            render_to_string('cards/standard/_section_stack_body.html', {'sections': sections, 'request': view.request})

    def test_a_table_added_after_the_stack_raises_at_the_call(self):
        view = _view()
        contact, _tags, _site = _cards(view)
        stack = view.add_card('customer', title='Customer').add_sections([contact])
        with self.assertRaisesMessage(ValueError, 'holds a section stack'):
            stack.add_table(Company)

    def test_a_click_on_the_bars_free_space_folds_and_the_controls_are_left_alone(self):
        script = render_to_string('cards/standard/_section_stack_script.html')
        self.assertIn("event.target.closest('.django-card__section-toggle, .django-card__section-menu')", script)
