"""``add_feed()``: rows on a rail of dots -- what happened, when, and who or what it concerned -- and the
figures ``add_facts()`` columns can now carry: an icon or a progress ring beside them, a note, a link."""
from django.test import RequestFactory, SimpleTestCase, override_settings
from decimal import Decimal

from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView

from cards.standard import BannerAction, CardMixin, FeedItem
from cards_examples.tests.test_escaping import PACKS, ROW_TEMPLATES

XSS = '<img src=x onerror=alert(1)>'


class _View(CardMixin, TemplateView):
    pass


def _card(template_name='default'):
    view = _View()
    view.request = RequestFactory().get('/')
    return view.add_card('probe', title='Probe', template_name=template_name)


def _everywhere(build):
    for pack in PACKS:
        with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
            for template_name in ROW_TEMPLATES:
                card = _card(template_name)
                build(card)
                yield pack, template_name, card.render()


class TestFeed(SimpleTestCase):
    def build(self, card):
        card.add_feed(
            [
                FeedItem('Bob became a qualified Estimator', when='10 Nov 2026', avatar='BF'),
                FeedItem('Call: price agreed', when='Today', meta='Phone call · Tom', tone='done',
                         badges=['Sticky', ('Overdue', 'late')], body=format_html('<p>{}</p>', 'Agreed £5k'),
                         actions=[BannerAction('Open', url='/event/1/'), {'label': 'Edit', 'attrs': {'data-x': '1'}}]),
                FeedItem('A link', url='/somewhere/', icon='fas fa-bell'),
                {'text': 'From a dict', 'tone': 'todo'},
            ],
            title='Activity', aside='4 of 9 · newest first', link_label='all in Events', link_url='/events/',
        )

    def test_every_part_reaches_the_page_in_every_pack_and_template(self):
        for pack, template_name, html in _everywhere(self.build):
            with self.subTest(pack=pack, template=template_name):
                self.assertIn('django-card__feed-rail', html)
                self.assertEqual(html.count('<li class="django-card__feed-row'), 4)
                self.assertIn('>Activity<', html)
                self.assertIn('4 of 9 · newest first', html)
                self.assertIn('href="/events/">all in Events<', html)
                self.assertIn('django-card__feed-avatar" aria-hidden="true">BF<', html)
                self.assertIn('django-card__feed-row--done', html)
                self.assertIn('django-card__feed-row--todo', html)
                self.assertIn('django-card__feed-badge--late">Overdue<', html)
                self.assertIn('django-card__feed-badge">Sticky<', html)
                self.assertIn('Phone call · Tom', html)

    def test_a_row_with_a_body_or_buttons_opens_and_a_row_with_a_url_is_a_link(self):
        card = _card()
        self.build(card)
        html = card.render()
        self.assertEqual(html.count('<details class="django-card__feed-details">'), 1)
        self.assertIn('<p>Agreed £5k</p>', html)
        self.assertIn('href="/event/1/"', html)
        self.assertIn('<button type="button" class="django-card__feed-action" data-x="1">', html)
        self.assertIn('<a class="django-card__feed-summary django-card__feed-link" href="/somewhere/">', html)

    def test_text_is_escaped_unless_marked_safe(self):
        card = _card()
        card.add_feed([FeedItem(XSS, when=XSS, meta=XSS, badges=[XSS], body=XSS, avatar=XSS)], title=XSS, aside=XSS)
        html = card.render()
        self.assertNotIn(XSS, html)
        self.assertIn('&lt;img src=x', html)

    def test_no_rows_shows_the_empty_message(self):
        card = _card()
        card.add_feed([], title='Activity', empty_title='Nothing logged yet', empty_text='Add an event.')
        html = card.render()
        self.assertNotIn('django-card__feed-rail', html)
        self.assertIn('<b>Nothing logged yet</b> Add an event.', html)

    def test_a_row_is_a_feed_item_or_a_dict(self):
        with self.assertRaises(TypeError):
            _card().add_feed(['a string'])

    def test_a_feed_with_nothing_to_show_adds_no_row(self):
        card = _card()
        card.add_feed([])
        self.assertEqual(card.rows, [])

    def test_a_link_label_needs_a_url(self):
        with self.assertRaisesMessage(ValueError, 'link_label needs a link_url'):
            _card().add_feed([FeedItem('x')], link_label='all in Events')

    def test_badges_are_checked_when_the_row_is_made(self):
        from django.utils.translation import gettext_lazy
        self.assertEqual(FeedItem('t', badges='Sticky').badges, [('Sticky', None)])
        self.assertEqual([str(text) for text, _tone in FeedItem('t', badges=gettext_lazy('Sticky')).badges], ['Sticky'])
        with self.assertRaisesMessage(ValueError, 'Feed badges are a list'):
            FeedItem('t', badges=('Overdue', 'late'))
        self.assertEqual(FeedItem('t', badges=['a', ['b', 'late']]).badges, [('a', None), ('b', 'late')])
        with self.assertRaisesMessage(ValueError, 'a (text, tone) pair'):
            FeedItem('t', badges=[('a', 'b', 'c')])

    def test_edge_inputs(self):
        with self.assertRaisesMessage(ValueError, 'needs its text'):
            FeedItem(None)
        with self.assertRaisesMessage(ValueError, 'needs its text'):
            FeedItem('   ')
        item = FeedItem('t', when=0, meta=Decimal('0'), avatar=' ', body='   ', badges=[None, '', (None, 'late'), 'Kept'])
        self.assertEqual((item.when, item.meta, item.avatar, item.body), ('0', '0', None, None))
        self.assertEqual(item.badges, [('Kept', None)])
        self.assertFalse(item.opens)
        self.assertEqual(len(FeedItem('t', actions=BannerAction('Open', url='/o/')).actions), 1)
        with self.assertRaisesMessage(ValueError, 'Feed badges are a list'):
            FeedItem('t', badges=3)
        card = _card()
        card.add_feed(FeedItem('one row'), title=0)
        html = card.render()
        self.assertIn('>one row<', html)
        self.assertIn('role="heading" aria-level="3">0<', html)

    def test_a_tone_is_said_in_words_too(self):
        card = _card()
        card.add_feed([FeedItem('x', tone='late'), FeedItem('y', tone='mine')])
        html = card.render()
        self.assertIn('<span class="django-card__feed-tone">Late</span>', html)
        self.assertEqual(html.count('django-card__feed-tone"'), 1)

    def test_a_link_label_and_url_alone_draw_a_head(self):
        card = _card()
        card.add_feed([], link_label='all in Events', link_url='/events/')
        self.assertIn('href="/events/">all in Events<', card.render())

    def test_a_row_that_opens_is_not_a_link_too(self):
        card = _card()
        card.add_feed([FeedItem('x', url='/elsewhere/', body='Body')])
        html = card.render()
        self.assertIn('<details', html)
        self.assertNotIn('/elsewhere/', html)

    def test_export_takes_a_row_each(self):
        card = _card()
        card.add_feed([FeedItem(format_html('<b>{}</b>', 'Bold'), when='Today'),
                       FeedItem(format_html('<b>{}</b>', '1 < 2')),
                       FeedItem('a < b and c > d')])
        self.assertEqual([row['value'] for row in card.get_export_data()], ['Bold', '1 < 2', 'a < b and c > d'])
        card = _card()
        card.add_feed([FeedItem('x', when=format_html('<i>{}</i>', 'Today'))])
        self.assertEqual(card.get_export_data()[0]['label'], 'Today')
        self.assertEqual(card.get_export_data()[0]['label'], 'Today')


class TestFactFigures(SimpleTestCase):
    def build(self, card):
        card.add_facts(
            {'lead': '4 lessons', 'note': 'done this week', 'icon': 'fas fa-fire'},
            {'lead': '3/7', 'note': 'path steps', 'ring': 43, 'url': '/path/', 'css_class': 'mine'},
            {'title': 'Plain', 'entries': [{'label': 'A', 'value': 'B'}]},
        )

    def test_an_icon_a_ring_a_note_and_a_link_in_every_pack_and_template(self):
        for pack, template_name, html in _everywhere(self.build):
            with self.subTest(pack=pack, template=template_name):
                self.assertEqual(html.count('django-card__facts-col--figure'), 2)
                self.assertIn('<i class="fas fa-fire django-card__facts-icon" aria-hidden="true"></i>', html)
                self.assertIn('style="--django-card-facts-ring: 43"', html)
                self.assertIn('aria-label="43%"', html)
                self.assertIn('<div class="django-card__facts-note">done this week</div>', html)
                self.assertIn('<a href="/path/" class="django-card__facts-col django-card__facts-col--figure '
                              'django-card__facts-col--link mine">', html)
                # a column with neither is as it was
                self.assertIn('<div class="django-card__facts-col"><div class="django-card__facts-content">'
                              '<div class="django-card__facts-title"', html)

    def test_a_ring_is_held_to_0_to_100_and_rounded_down(self):
        for given, drawn in ((-5, 0), (150, 100), (0, 0), (43.7, 43), ('50', 50), (99.5, 99), (100, 100)):
            card = _card()
            card.add_facts({'lead': 'x', 'ring': given})
            self.assertIn(f'--django-card-facts-ring: {drawn}"', card.render())

    def test_a_ring_that_is_no_number_says_so(self):
        for given in ('abc', '43%', '', float('nan'), float('inf'), object(), True, False, b'50'):
            with self.subTest(given=given), self.assertRaisesMessage(ValueError, "ring is a percentage"):
                _card().add_facts({'lead': 'x', 'ring': given})

    def test_a_linked_column_refuses_entries_that_are_links_menus_or_buttons_themselves(self):
        for extra in ({'link': '/entry/'}, {'value_link': '/v/'}, {'copy_to_clipboard': True}, {'auto_link': True},
                      {'popover': 'More'}, {'html_override': '<a href="/h/">%1%</a>'}):
            with self.subTest(extra=extra), self.assertRaisesMessage(ValueError, 'is one link'):
                _card().add_facts({'lead': 'x', 'url': '/col/', 'entries': [{'label': 'L', 'value': 'V', **extra}]})
        with self.assertRaisesMessage(ValueError, 'is one link'):  # on the lead, and from extra_row_kwargs
            _card().add_facts({'lead': {'value': 'x', 'link': '/l/'}, 'url': '/col/'})
        with self.assertRaisesMessage(ValueError, 'is one link'):
            _card().add_facts({'lead': 'x', 'url': '/col/'}, extra_row_kwargs={'value_link': '/v/'})
        # plain entries are fine, and an empty menu is no menu
        _card().add_facts({'lead': 'x', 'url': '/col/', 'entries': [{'label': 'L', 'value': 'V', 'menu': []}]})

    def test_a_column_with_nothing_but_a_figure_or_a_note_is_refused(self):
        for column in ({'icon': 'fas fa-fire', 'note': 'alone'}, {'ring': 43, 'note': 'steps'}, {'title': '', 'icon': 'x'}):
            with self.subTest(column=column), self.assertRaisesMessage(ValueError, 'needs a lead, entries or a title'):
                _card().add_facts(column)

    def test_a_column_whose_entries_are_all_hidden_is_left_out(self):
        card = _card()
        card.add_facts({'icon': 'fas fa-fire', 'entries': [{'label': 'L', 'value': 'V', 'hidden': True}]},
                       {'lead': 'kept'})
        self.assertEqual(len(card.rows[0]['columns']), 1)

    def test_plain_text_that_looks_like_a_tag_is_fine_in_a_linked_column(self):
        card = _card()
        card.add_facts({'url': '/u/', 'lead': 'Margin <a third', 'entries': [{'label': 'L', 'value': 'press <button>'}]})
        self.assertIn('Margin &lt;a third', card.render())

    def test_safe_markup_with_a_link_is_refused_anywhere_in_a_linked_column(self):
        link = mark_safe('<a href="/x/">x</a>')
        for column in ({'url': '/u/', 'lead': 'x', 'note': link}, {'url': '/u/', 'lead': 'x', 'title': link},
                       {'url': '/u/', 'lead': 'x', 'entries': [{'label': link, 'value': 'V'}]}):
            with self.subTest(column=column), self.assertRaisesMessage(ValueError, 'is one link'):
                _card().add_facts(column)

    def test_a_zero_note_is_shown(self):
        card = _card()
        card.add_facts({'lead': 'x', 'note': 0})
        self.assertIn('<div class="django-card__facts-note">0</div>', card.render())

    def test_export_takes_a_columns_note_and_ring(self):
        card = _card()
        card.add_facts({'title': 'Path', 'lead': '3/7', 'note': 'steps done', 'ring': 43})
        data = card.get_export_data()
        self.assertIn({'label': 'Path', 'value': 'steps done'}, data)
        self.assertIn({'label': 'Path', 'value': '43%'}, data)
