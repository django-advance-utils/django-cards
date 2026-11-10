"""add_banner_tiles(): a master card whose body is a grid of larger banner tiles."""
import dataclasses
import os
import re

from django.test import RequestFactory, TestCase
from django.utils.html import format_html
from django.views.generic import TemplateView

from cards.standard import CardMixin, BannerAction, BannerTile


_TEMPLATES = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))), "cards", "templates", "cards")


class _BannerTileCardView(CardMixin, TemplateView):
    pass


class TestBannerTiles(TestCase):
    def setUp(self):
        self.view = _BannerTileCardView()
        self.view.request = RequestFactory().get('/')

    def render(self, tiles, **kwargs):
        card = self.view.add_card('demo', title='Master')
        card.add_banner_tiles(tiles, **kwargs)
        return card.render()

    def test_the_master_card_keeps_its_header(self):
        html = self.render([BannerTile(key='c1', title='Getting Started')])
        self.assertIn('Master', html)
        self.assertIn('django-card__banner-tiles', html)
        self.assertIn('id="c1"', html)
        self.assertIn('>Getting Started<', html)

    def test_every_field_reaches_the_tile(self):
        html = self.render([BannerTile(
            key='c1', title='T', description='Desc', banner_label='Projects',
            banner_icon='fas fa-folder', banner_background='#123456', step='Step 1 of 2',
            badge='Required', stats=[('fas fa-play', '13 lessons'), '8 quizzes'],
            progress=30, status='Not started', footer_label='Cat', footer_icon='fas fa-tag',
            action_label='Start', action_url='/start/', css_class='mine')])
        for part in ('banner-tile-description', 'banner-tile-banner-label', 'banner-tile-banner-watermark',
                     'banner-tile-step', 'banner-tile-badge', 'banner-tile-stats', 'banner-tile-status',
                     'banner-tile-footer', 'django-card__banner-tile mine'):
            self.assertIn(part, html)
        self.assertIn('background: #123456', html)
        self.assertIn('width: 30%', html)
        self.assertIn('href="/start/"', html)
        self.assertIn('8 quizzes', html)

    def test_a_tile_draws_only_what_it_was_given(self):
        html = self.render([BannerTile(key='c1', title='T')])
        for part in ('banner-tile-description', 'banner-tile-step', 'banner-tile-badge', 'banner-tile-stats',
                     'banner-tile-progress', 'banner-tile-status', 'banner-tile-footer'):
            self.assertNotIn(part, html)

    def test_zero_progress_draws_an_empty_bar(self):
        self.assertIn('width: 0%', self.render([BannerTile(key='c1', title='T', progress=0)]))

    def test_progress_is_clamped(self):
        self.assertIn('width: 100%', self.render([BannerTile(key='c1', title='T', progress=250)]))

    def test_text_fields_are_escaped(self):
        html = self.render([BannerTile(key='c1', title='<script>x</script>',
                                       description='<b>d</b>', badge='<i>b</i>')])
        self.assertNotIn('<script>x', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<b>d</b>', html)

    def test_dicts_are_accepted_and_typos_raise(self):
        self.assertIn('id="c1"', self.render([{'key': 'c1', 'title': 'T'}]))
        with self.assertRaises(TypeError):
            self.render([{'key': 'c1', 'title': 'T', 'titel': 'oops'}])

    def test_empty_message(self):
        self.assertIn('Nothing yet', self.render([], empty_message='Nothing yet'))

    def test_width_sets_the_custom_property(self):
        html = self.render([BannerTile(key='c1', title='T')], width='300px')
        self.assertIn('--django-card-banner-tile-width: 300px', html)


class TestBannerTileDetailLayout(TestCase):
    def setUp(self):
        self.view = _BannerTileCardView()
        self.view.request = RequestFactory().get('/')

    def render(self, tiles):
        card = self.view.add_card('demo', border='none')
        card.add_banner_tiles(tiles)
        return card.render()

    def detail(self, **kwargs):
        return BannerTile(key='d1', layout='detail', **kwargs)

    def test_every_detail_part_is_drawn(self):
        html = self.render([self.detail(
            banner_url='/preview/', banner_caption='Preview this course',
            callout_icon='fas fa-route', callout_title='On your path', callout_text='Step 1 of 2.',
            callout_link_label='See your path', callout_link_url='/path/',
            stats=[('fas fa-award', 'Certificate of completion')],
            action_label='Start this course', action_url='/start/',
            secondary_label='Save for later', secondary_url='/save/', note='Saved as you go.')])
        self.assertIn('django-card__banner-tile-detail', html)
        self.assertIn('href="/preview/"', html)
        self.assertIn('django-card__banner-tile-play', html)
        self.assertIn('Preview this course', html)
        self.assertIn('django-card__banner-tile-callout', html)
        self.assertIn('href="/path/"', html)
        self.assertIn('django-card__banner-tile-stats--list', html)
        self.assertIn('class="btn btn-primary django-card__banner-tile-action"', html)
        self.assertIn('href="/save/"', html)
        self.assertIn('Saved as you go.', html)

    def test_the_detail_button_is_in_the_body_not_a_footer(self):
        html = self.render([self.detail(action_label='Start', action_url='/start/')])
        self.assertNotIn('django-card__banner-tile-footer', html)
        self.assertEqual(html.count('href="/start/"'), 1)

    def test_compact_draws_none_of_the_detail_parts(self):
        html = self.render([BannerTile(key='c1', title='T', note='n', secondary_label='s')])
        for part in ('banner-tile-detail', 'banner-tile-play', 'banner-tile-note', 'banner-tile-secondary',
                     'banner-tile-stats--list'):
            self.assertNotIn(part, html)

    def test_callout_text_is_escaped(self):
        html = self.render([self.detail(callout_title='<b>x</b>', callout_text='<i>y</i>')])
        self.assertNotIn('<b>x</b>', html)
        self.assertNotIn('<i>y</i>', html)

    def test_an_unknown_layout_raises(self):
        with self.assertRaises(ValueError):
            BannerTile(key='x', layout='wide')


class TestBannerTileHighlightLayout(TestCase):
    def setUp(self):
        self.view = _BannerTileCardView()
        self.view.request = RequestFactory().get('/')

    def render(self, tiles):
        card = self.view.add_card('demo', title='Master')
        card.add_banner_tiles(tiles)
        return card.render()

    def test_every_highlight_part_is_drawn(self):
        html = self.render([BannerTile(
            key='p1', layout='highlight', banner_label='Your learning path',
            banner_icon='fas fa-drafting-compass', title='Estimator', description='From call to order.',
            status='0 of 2 steps done', progress=0, action_label='Continue', action_url='/go/')])
        self.assertIn('django-card__banner-tile-highlight', html)
        self.assertIn('Your learning path', html)
        self.assertIn('django-card__banner-tile-highlight-title', html)
        self.assertIn('0 of 2 steps done', html)
        self.assertIn('django-card__banner-tile-highlight-progress', html)
        self.assertIn('class="btn django-card__banner-tile-highlight-action"', html)
        self.assertIn('href="/go/"', html)

    def test_highlight_has_no_banner_or_footer(self):
        html = self.render([BannerTile(key='p1', layout='highlight', title='T',
                                       footer_label='x', action_label='Go')])
        self.assertNotIn('django-card__banner-tile-banner', html)
        self.assertNotIn('django-card__banner-tile-footer', html)

    def test_background_sits_on_the_tile(self):
        html = self.render([BannerTile(key='p1', layout='highlight', title='T',
                                       banner_background='#123456')])
        self.assertIn('id="p1" style="background: #123456"', html)

    def test_it_sits_in_a_grid_beside_compact_tiles(self):
        html = self.render([BannerTile(key='p1', layout='highlight', title='Path'),
                            BannerTile(key='c1', title='Course')])
        self.assertLess(html.index('id="p1"'), html.index('id="c1"'))
        self.assertEqual(len(re.findall(r'django-card__banner-tile[ "]', html)), 2)

    def test_highlight_text_is_escaped(self):
        html = self.render([BannerTile(key='p1', layout='highlight', title='<b>x</b>',
                                       banner_label='<i>y</i>')])
        self.assertNotIn('<b>x</b>', html)
        self.assertNotIn('<i>y</i>', html)


class TestBannerTileFeatureAndSlider(TestCase):
    def setUp(self):
        self.view = _BannerTileCardView()
        self.view.request = RequestFactory().get('/')

    def render(self, tiles, **kwargs):
        card = self.view.add_card('promo', border='none')
        card.add_banner_tiles(tiles, **kwargs)
        return card.render()

    def feature(self, key='f1', **kwargs):
        return BannerTile(key=key, layout='feature', title='T', **kwargs)

    def test_feature_with_an_icon_draws_both_shapes_and_the_icon(self):
        html = self.render([self.feature(banner_icon='fas fa-compass', description='D',
                                         action_label='Go', action_url='/go/')])
        self.assertIn('django-card__banner-tile-feature-shape--accent', html)
        self.assertIn('django-card__banner-tile-feature-shape--grey', html)
        self.assertIn('django-card__banner-tile-feature-icon', html)
        self.assertIn('class="btn django-card__banner-tile-feature-action"', html)
        self.assertNotIn('django-card__banner-tile-feature--plain', html)

    def test_feature_without_an_icon_is_plain(self):
        html = self.render([self.feature()])
        self.assertIn('django-card__banner-tile-feature--plain', html)
        self.assertNotIn('django-card__banner-tile-feature-shape--accent', html)
        self.assertNotIn('django-card__banner-tile-feature-icon', html)

    def test_no_slider_unless_asked(self):
        html = self.render([self.feature()])
        self.assertNotIn('django-card__banner-tile-slider', html)
        self.assertNotIn("getElementById('promo_slider')", html)

    def test_slider_has_arrows_a_dot_per_tile_and_its_script(self):
        html = self.render([self.feature('a'), self.feature('b'), BannerTile(key='c', title='C')],
                           slider=True)
        self.assertIn('id="promo_slider"', html)
        self.assertIn('django-card__banner-tiles--slider', html)
        self.assertIn('django-card__banner-tile-slider-arrow--prev', html)
        self.assertIn('django-card__banner-tile-slider-arrow--next', html)
        self.assertEqual(html.count('aria-label="Go to slide'), 3)
        self.assertIn("getElementById('promo_slider')", html)

    def test_feature_text_is_escaped(self):
        html = self.render([BannerTile(key='f', layout='feature', title='<b>x</b>',
                                       description='<i>y</i>')])
        self.assertNotIn('<b>x</b>', html)
        self.assertNotIn('<i>y</i>', html)


class TestBannerTilePlainLayoutAndTitleHtml(TestCase):
    def setUp(self):
        self.view = _BannerTileCardView()
        self.view.request = RequestFactory().get('/')

    def render(self, tiles):
        card = self.view.add_card('demo', border='none')
        card.add_banner_tiles(tiles)
        return card.render()

    def test_plain_draws_title_and_description_only(self):
        html = self.render([BannerTile(key='p', layout='plain', title='Learn',
                                       description='Pick a stage.')])
        self.assertIn('django-card__banner-tile-plain-title', html)
        self.assertIn('Pick a stage.', html)
        for part in ('banner-tile-banner', 'banner-tile-footer', 'banner-tile-progress', 'banner-tile-plain-action'):
            self.assertNotIn(part, html)

    def test_plain_link(self):
        html = self.render([BannerTile(key='p', layout='plain', title='T',
                                       action_label='All courses', action_url='/all/')])
        self.assertIn('class="django-card__banner-tile-plain-action"', html)
        self.assertIn('href="/all/"', html)

    def test_title_html_is_rendered_as_markup(self):
        html = self.render([BannerTile(key='p', layout='plain',
                                       title_html=format_html('Learn <em>every</em> part of {}', 'X'))])
        self.assertIn('Learn <em>every</em> part of X', html)

    def test_format_html_still_escapes_what_goes_into_title_html(self):
        html = self.render([BannerTile(key='p', layout='plain',
                                       title_html=format_html('<em>{}</em>', '<script>x</script>'))])
        self.assertNotIn('<script>x', html)

    def test_plain_title_is_escaped(self):
        html = self.render([BannerTile(key='p', layout='plain', title='<em>x</em>')])
        self.assertNotIn('<em>x</em>', html)

    def test_title_html_works_in_every_layout(self):
        for layout in ('compact', 'detail', 'highlight', 'feature', 'plain'):
            with self.subTest(layout=layout):
                html = self.render([BannerTile(key='p', layout=layout,
                                               title_html=format_html('<em>{}</em>', 'hi'))])
                self.assertIn('<em>hi</em>', html)


class TestBannerTileShowcaseLayout(TestCase):
    def setUp(self):
        self.view = _BannerTileCardView()
        self.view.request = RequestFactory().get('/')

    def render(self, tiles):
        card = self.view.add_card('demo', border='none')
        card.add_banner_tiles(tiles)
        return card.render()

    def showcase(self, **kwargs):
        return BannerTile(key='s', layout='showcase', title='Fits together', **kwargs)

    def test_every_showcase_part_is_drawn(self):
        html = self.render([self.showcase(
            description='One map.', points=[('fas fa-cubes', 'Every area'), ('fas fa-cog', 'Settings', '#123456')],
            banner_icon='fas fa-project-diagram', flow=['CRM', 'Projects', 'Gantt'],
            panel_icon='fas fa-cog', action_label='Open the map', action_url='/map/')])
        self.assertIn('django-card__banner-tile-showcase-points', html)
        self.assertIn('Every area', html)
        self.assertIn('background: #e3cde6', html)   # the first default colour
        self.assertIn('background: #123456', html)   # a point's own colour
        self.assertIn('django-card__banner-tile-showcase-panel--main', html)
        self.assertEqual(html.count('django-card__banner-tile-showcase-flow-node'), 3)
        self.assertEqual(html.count('django-card__banner-tile-showcase-flow-line'), 2)
        self.assertIn('django-card__banner-tile-showcase-panel--icon', html)
        self.assertIn('class="btn django-card__banner-tile-showcase-action"', html)
        self.assertIn('href="/map/"', html)

    def test_no_panels_means_text_only(self):
        html = self.render([self.showcase()])
        self.assertNotIn('django-card__banner-tile-showcase-panels', html)

    def test_only_the_panels_given_are_drawn(self):
        html = self.render([self.showcase(flow=['A', 'B'])])
        self.assertIn('django-card__banner-tile-showcase-panel--flow', html)
        self.assertNotIn('django-card__banner-tile-showcase-panel--main', html)
        self.assertNotIn('django-card__banner-tile-showcase-panel--icon', html)

    def test_showcase_text_is_escaped(self):
        html = self.render([self.showcase(points=[('fas fa-cog', '<b>p</b>')], flow=['<i>f</i>'])])
        self.assertNotIn('<b>p</b>', html)
        self.assertNotIn('<i>f</i>', html)

    def test_a_malformed_point_raises(self):
        with self.assertRaises(ValueError):
            self.render([self.showcase(points=['just text'])])


class TestBannerTileReviewFixes(TestCase):
    def setUp(self):
        self.view = _BannerTileCardView()
        self.view.request = RequestFactory().get('/')

    def test_bad_progress_fails_when_the_tile_is_built(self):
        for progress in ('50%', float('nan'), object()):
            with self.subTest(progress=progress), self.assertRaises(ValueError):
                BannerTile(key='c', title='T', progress=progress)

    def test_progress_clamps_an_infinity_and_accepts_a_numeric_string(self):
        self.assertEqual(BannerTile(key='c', progress=float('inf')).progress_percent, 100)
        self.assertEqual(BannerTile(key='c', progress='42.7').progress_percent, 43)

    def test_bad_stats_and_points_fail_when_the_tile_is_built_in_any_layout(self):
        with self.assertRaises(ValueError):
            BannerTile(key='c', stats=[('a', 'b', 'c')])
        with self.assertRaises(ValueError):
            BannerTile(key='c', points=['just text'])   # compact, which never draws points

    def test_the_button_follows_a_layout_changed_after_construction(self):
        tile = dataclasses.replace(BannerTile(key='c', title='T'), layout='highlight')
        self.assertEqual(tile.action_classes, 'btn django-card__banner-tile-highlight-action')
        tile.layout = 'detail'
        self.assertEqual(tile.action_classes, 'btn btn-primary')
        self.assertEqual(BannerTile(key='c', layout='detail', action_css_class='x').action_classes, 'x')

    def test_a_highlight_icon_without_a_label_is_drawn(self):
        card = self.view.add_card('demo', title='M')
        card.add_banner_tiles([BannerTile(key='h', layout='highlight', title='T',
                                          banner_icon='fas fa-route')])
        self.assertIn('<i class="fas fa-route"></i></div>', card.render())

    def test_a_later_call_can_turn_the_slider_off_and_none_keeps_it(self):
        card = self.view.add_card('demo', title='M')
        card.add_banner_tiles([BannerTile(key='a')], slider=True)
        card.add_banner_tiles([BannerTile(key='b')])
        self.assertTrue(card.extra_card_info['banner_tiles_slider'])
        card.add_banner_tiles([BannerTile(key='c')], slider=False)
        self.assertNotIn('django-card__banner-tiles--slider', card.render())

    def test_heading_escapes_title_and_passes_title_html(self):
        self.assertEqual(str(BannerTile(key='c', title='<b>x</b>').heading), '<b>x</b>')
        card = self.view.add_card('demo', title='M')
        card.add_banner_tiles([BannerTile(key='a', title='<b>x</b>'),
                               BannerTile(key='b', title_html=format_html('<em>{}</em>', 'y'))])
        html = card.render()
        self.assertIn('&lt;b&gt;x&lt;/b&gt;', html)
        self.assertIn('<em>y</em>', html)

    def test_both_packs_share_one_tiles_body(self):
        for pack in ('bootstrap4', 'bootstrap5'):
            with open(f'{_TEMPLATES}/{pack}/standard/banner_tiles.html') as f:
                source = f.read()
            self.assertIn("{% include 'cards/standard/_banner_tiles_body.html' %}", source)
            self.assertNotIn('tile.', source)


class TestBannerTileProgressGroup(TestCase):
    """The bar and status are pinned to the bottom of a compact tile, so a row's bars line up."""

    def setUp(self):
        self.view = _BannerTileCardView()
        self.view.request = RequestFactory().get('/')

    def group(self, **fields):
        card = self.view.add_card('demo', title='M')
        card.add_banner_tiles([BannerTile(key='c', title='T', **fields)])
        html = card.render()
        start = html.find('<div class="django-card__banner-tile-progress-group">')
        if start == -1:
            return None
        # Walk the divs to the group's own closing tag; its children are divs too.
        depth = 0
        for tag in re.finditer(r'<div\b|</div>', html[start:]):
            depth += 1 if tag.group() == '<div' else -1
            if depth == 0:
                return html[start:start + tag.end()]

    def test_bar_and_status_are_in_the_group_in_that_order(self):
        group = self.group(progress=45, status='45% complete')
        self.assertLess(group.index('role="progressbar"'), group.index('45% complete'))

    def test_a_bar_without_a_status_keeps_an_empty_status_line(self):
        group = self.group(progress=60)
        self.assertIn('<div class="django-card__banner-tile-status"></div>', group)

    def test_a_status_without_a_bar_is_in_the_group_alone(self):
        group = self.group(status='Archived')
        self.assertIn('Archived', group)
        self.assertNotIn('role="progressbar"', group)

    def test_neither_means_no_group(self):
        self.assertIsNone(self.group())


class TestBannerTileFinalReviewFixes(TestCase):
    def setUp(self):
        self.view = _BannerTileCardView()
        self.view.request = RequestFactory().get('/')

    def render(self, tiles, **kwargs):
        card = self.view.add_card('demo', title='M')
        card.add_banner_tiles(tiles, **kwargs)
        return card.render()

    def test_a_bare_string_for_a_list_field_is_refused(self):
        for name in ('stats', 'points', 'flow'):
            with self.subTest(name), self.assertRaises(TypeError):
                BannerTile(key='c', **{name: 'oops'})
        BannerTile(key='c', stats=('a', 'b'), flow=None)   # a tuple or None is fine

    def test_a_banner_link_with_no_text_is_named_for_screen_readers(self):
        html = self.render([BannerTile(key='a', title='Intro', banner_url='/p/'),
                            BannerTile(key='b', layout='detail', banner_url='/q/')])
        self.assertIn('href="/p/" class="django-card__banner-tile-banner django-card__banner-tile-banner--link" '
                      'aria-label="Intro"', html)
        self.assertIn('aria-label="Preview"', html)

    def test_a_banner_link_with_a_caption_needs_no_label(self):
        html = self.render([BannerTile(key='a', title='Intro', banner_url='/p/', banner_caption='Watch')])
        self.assertNotIn('aria-label="Intro"', html)

    def test_an_empty_slider_is_just_the_empty_message(self):
        html = self.render([], slider=True, empty_message='Nothing yet')
        self.assertIn('Nothing yet', html)
        self.assertNotIn('django-card__banner-tile-slider', html)
        self.assertNotIn('django-card__banner-tiles--slider', html)
        self.assertNotIn("getElementById('demo_slider')", html)


class TestBannerTileSecondReviewFixes(TestCase):
    def setUp(self):
        self.view = _BannerTileCardView()
        self.view.request = RequestFactory().get('/')

    def render(self, tiles, **kwargs):
        card = self.view.add_card('demo', title='M')
        card.add_banner_tiles(tiles, **kwargs)
        return card, card.render()

    def test_the_empty_message_spans_the_grid(self):
        with open(os.path.join(os.path.dirname(_TEMPLATES), '..', 'static', 'cards', 'css', 'cards.css')) as f:
            css = f.read()
        self.assertRegex(css, r'\.django-card__banner-tiles > \.django-card__tiles-empty \{\s*grid-column: 1 / -1;')
        _, html = self.render([], empty_message='Nothing yet')
        self.assertRegex(html, r'<div class="django-card__banner-tiles"[^>]*>\s*<p class="django-card__tiles-empty">Nothing yet')

    def test_a_title_html_banner_link_is_named_from_its_text(self):
        _, html = self.render([BannerTile(key='a', layout='detail', banner_url='/p/',
                                          title_html=format_html('Learn <em>{}</em> &amp; more', 'X'))])
        self.assertIn('aria-label="Learn X &amp; more"', html)

    def test_plain_title(self):
        self.assertEqual(BannerTile(key='a', title='T', title_html='<b>H</b>').plain_title, 'T')
        self.assertEqual(BannerTile(key='a', title_html='<b>H</b>').plain_title, 'H')
        self.assertIsNone(BannerTile(key='a', title_html='<i class="x"></i>').plain_title)
        self.assertIsNone(BannerTile(key='a').plain_title)

    def test_the_slider_flag_is_worked_out_once_and_follows_later_calls(self):
        card, _ = self.render([], slider=True)
        self.assertFalse(card.extra_card_info['banner_tiles_is_slider'])
        card.add_banner_tiles([BannerTile(key='a')])
        self.assertTrue(card.extra_card_info['banner_tiles_is_slider'])
        card.add_banner_tiles([], slider=False)
        self.assertFalse(card.extra_card_info['banner_tiles_is_slider'])

    def test_the_slider_hides_its_dots_when_nothing_overflows(self):
        _, html = self.render([BannerTile(key='a')], slider=True)
        self.assertIn("dotRow.style.display = overflows() ? '' : 'none';", html)


class TestBannerTileThirdReviewFixes(TestCase):
    def setUp(self):
        self.view = _BannerTileCardView()
        self.view.request = RequestFactory().get('/')

    def test_progress_is_rounded_not_truncated(self):
        self.assertEqual(BannerTile(key='c', progress=99.6).progress_percent, 100)
        self.assertEqual(BannerTile(key='c', progress=0.9).progress_percent, 1)
        self.assertEqual(BannerTile(key='c', progress=42.4).progress_percent, 42)

    def test_one_bad_tile_leaves_the_card_as_it_was(self):
        card = self.view.add_card('demo', title='M')
        card.add_banner_tiles([BannerTile(key='a')])
        before = dict(card.extra_card_info)
        with self.assertRaises(ValueError):
            card.add_banner_tiles([{'key': 'b'}, {'key': 'c', 'progress': 'n/a'}], slider=True)
        self.assertEqual([t.key for t in card.extra_card_info['banner_tiles']], ['a'])
        self.assertNotIn('banner_tiles_slider', card.extra_card_info)
        self.assertEqual(card.extra_card_info['banner_tiles_is_slider'], before['banner_tiles_is_slider'])


class TestBannerTileInlineStyles(TestCase):
    """The banner background and a showcase point's colour are written into ``style`` attributes.

    Escaping is no defence there -- a semicolon is left alone, so a stored
    ``red;position:fixed;inset:0`` would add declarations and lift the element over the page. Both
    are checked instead: a background has to be a colour or a gradient (``css_background``), a
    point's colour a colour (``css_colour``), and anything else is dropped -- the banner keeping the
    stylesheet's own, the point taking its turn from the soft colours as one given none does.
    """
    PAYLOAD = 'red;position:fixed;inset:0'

    def setUp(self):
        self.view = _BannerTileCardView()
        self.view.request = RequestFactory().get('/')

    def render(self, tiles):
        card = self.view.add_card('demo', title='Master')
        card.add_banner_tiles(tiles)
        return card.render()

    def test_a_colour_or_gradient_background_is_drawn_in_every_layout(self):
        for background in ('#123456', 'linear-gradient(135deg, #7b2ff7 0%, #3d1a8c 100%)',
                           'radial-gradient(circle at top, var(--a, #fff), transparent)',
                           'linear-gradient(red, blue), linear-gradient(green, yellow)',
                           '#e6f0fb center / cover no-repeat'):
            for layout in ('compact', 'detail', 'highlight', 'feature', 'showcase'):
                with self.subTest(background=background, layout=layout):
                    html = self.render([BannerTile(key='t1', title='T', layout=layout,
                                                   banner_icon='fas fa-star', banner_background=background)])
                    self.assertIn(f'background: {background}', html)

    def test_a_background_that_is_not_one_is_dropped_in_every_layout(self):
        for background in (self.PAYLOAD, 'url(https://example.com/x.png)', '#123456;top:0',
                           'linear-gradient(red, blue);top:0', 'expression(alert(1))'):
            for layout in ('compact', 'detail', 'highlight', 'feature', 'showcase'):
                with self.subTest(background=background, layout=layout):
                    html = self.render([BannerTile(key='t1', title='T', layout=layout,
                                                   banner_icon='fas fa-star', banner_background=background)])
                    self.assertNotIn(background, html)
                    self.assertNotIn('position:fixed', html)
                    self.assertNotIn('url(https://example.com', html)
                    # Dropped, not written empty: an inline `background:` of nothing would still
                    # override the stylesheet's default.
                    self.assertNotIn('style="background:', html)
                    self.assertNotIn('None', html)

    def test_a_point_colour_is_kept_when_it_is_one(self):
        for colour in ('var(--ok, green)', 'linear-gradient(135deg, #7b2ff7, #3d1a8c)'):
            with self.subTest(colour=colour):
                html = self.render([BannerTile(key='s1', title='T', layout='showcase',
                                               points=[('fas fa-check', 'One', colour)])])
                self.assertIn(f'style="background: {colour}"', html)

    def test_a_point_colour_that_is_not_one_takes_its_turn(self):
        html = self.render([BannerTile(key='s1', title='T', layout='showcase',
                                       points=[('fas fa-check', 'One', self.PAYLOAD),
                                               ('fas fa-check', 'Two', 'url(x)')])])
        self.assertNotIn('position:fixed', html)
        self.assertNotIn('url(x)', html)
        self.assertIn(f'style="background: {BannerTile.POINT_COLOURS[0]}"', html)
        self.assertIn(f'style="background: {BannerTile.POINT_COLOURS[1]}"', html)


class TestBannerTileLinksLocksActionsAndFilters(TestCase):
    """1.9.2: a tile that is a link as a whole, a locked tile, buttons the page's script answers, and filters."""

    def setUp(self):
        self.view = _BannerTileCardView()
        self.view.request = RequestFactory().get('/')

    def render(self, tiles, **kwargs):
        card = self.view.add_card('demo', title='Master')
        card.add_banner_tiles(tiles, **kwargs)
        return card.render()

    def test_a_url_makes_the_whole_tile_a_link_under_its_own_button(self):
        html = self.render([BannerTile(key='c1', title='Joinery <basics>', url='/courses/1/',
                                       action_label='Start', action_url='/start/')])
        self.assertIn('django-card__banner-tile--linked', html)
        self.assertIn('<a href="/courses/1/" class="django-card__banner-tile-link" aria-label="Joinery &lt;basics&gt;"></a>',
                      html)
        self.assertIn('href="/start/"', html)

    def test_a_tile_with_no_url_is_no_link(self):
        html = self.render([BannerTile(key='c1', title='T')])
        self.assertNotIn('banner-tile-link', html)
        self.assertNotIn('banner-tile--linked', html)

    def test_a_locked_tile_links_nowhere_and_says_why(self):
        html = self.render([BannerTile(key='c1', title='T', url='/courses/1/', banner_url='/preview/',
                                       locked='Finish step <2> first', progress=40, status='40%',
                                       action_label='Start', action_url='/start/')])
        self.assertIn('django-card__banner-tile--locked', html)
        self.assertIn('title="Finish step &lt;2&gt; first"', html)
        self.assertIn('<i class="fas fa-lock"></i> Finish step &lt;2&gt; first', html)
        for gone in ('/courses/1/', '/preview/', '/start/', 'width: 40%', 'banner-tile-play'):
            self.assertNotIn(gone, html)

    def test_locked_as_true_says_locked(self):
        html = self.render([BannerTile(key='c1', title='T', locked=True)])
        self.assertIn('<i class="fas fa-lock"></i> Locked', html)
        self.assertNotIn(' title="', html.split('banner-tile-lock')[1].split('>')[0])

    def test_a_locked_detail_tile_draws_its_button_disabled_and_no_secondaries(self):
        html = self.render([BannerTile(key='c1', layout='detail', action_label='Start', action_url='/start/',
                                       secondary_label='Save', secondary_url='/save/', locked=True)])
        self.assertRegex(html, r'<button type="button" disabled class="btn btn-primary '
                               r'django-card__banner-tile-action">Start <i class="fas fa-lock"></i></button>')
        self.assertNotIn('/save/', html)
        self.assertNotIn('banner-tile-secondaries', html)

    def test_an_action_with_no_url_is_a_button_carrying_its_data_attributes(self):
        html = self.render([BannerTile(key='c1', layout='detail', action=BannerAction(
            'Start <now>', icon='fas fa-arrow-right', attrs={'data-course-button': 'start"x'}))])
        self.assertIn('<button type="button" class="btn btn-primary django-card__banner-tile-action" '
                      'data-course-button="start&quot;x">Start &lt;now&gt; <i class="fas fa-arrow-right"></i></button>',
                      html)

    def test_an_action_takes_only_data_and_aria_attributes(self):
        for name in ('onclick', 'href', 'class', 'data-', 'Data-x', 'data-x y'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                BannerAction('Go', attrs={name: 'x'})
        BannerAction('Go', attrs={'data-x': '1', 'aria-describedby': 'y'})

    def test_secondary_actions_follow_the_secondary_link(self):
        html = self.render([BannerTile(
            key='c1', layout='detail', secondary_label='Save', secondary_url='/save/',
            secondary_actions=[BannerAction('Restart', icon='fas fa-redo', attrs={'data-b': 'restart'}),
                               {'label': 'Leave', 'attrs': {'data-b': 'leave'}}])])
        save, restart, leave = html.index('/save/'), html.index('Restart'), html.index('Leave')
        self.assertLess(save, restart)
        self.assertLess(restart, leave)
        self.assertIn('<button type="button" class="django-card__banner-tile-secondary" data-b="restart">'
                      '<i class="fas fa-redo"></i> Restart</button>', html)

    def test_an_action_label_still_draws_as_before(self):
        detail = self.render([BannerTile(key='c1', layout='detail', action_label='Go', action_url='/go/')])
        self.assertIn('<a href="/go/" class="btn btn-primary django-card__banner-tile-action">Go '
                      '<i class="fas fa-arrow-right"></i></a>', detail)
        compact = self.render([BannerTile(key='c2', action_label='Go')])
        self.assertIn('<a href="#" class="btn btn-sm btn-outline-primary">Go</a>', compact)

    def test_filters_draw_buttons_and_mark_each_tile(self):
        html = self.render([BannerTile(key='c1', title='A', filter_keys=['crm']),
                            BannerTile(key='c2', title='B', filter_keys=['gantt', 'crm'])],
                           filters=['crm', ('gantt', 'The <Gantt>')], filter_style='tabs', subtitle='Pick <one>')
        self.assertIn('django-card__banner-tile-filters--tabs', html)
        self.assertIn('<p class="django-card__banner-tiles-subtitle">Pick &lt;one&gt;</p>', html)
        self.assertIn('data-banner-filter="" class="active" aria-pressed="true">All</button>', html)
        self.assertIn('data-banner-filter="gantt" aria-pressed="false">The &lt;Gantt&gt;</button>', html)
        self.assertIn('data-banner-filters="[&quot;gantt&quot;, &quot;crm&quot;]"', html)
        self.assertIn('id="demo_filters"', html)
        self.assertNotIn(' hidden', html)

    def test_a_selected_filter_hides_the_others_as_the_page_is_drawn(self):
        html = self.render([BannerTile(key='c1', title='A', filter_keys=['crm']),
                            BannerTile(key='c2', title='B', filter_keys=['gantt'])],
                           filters=['crm', 'gantt'], filter_selected='gantt', filter_all_label='')
        self.assertNotIn('data-banner-filter=""', html)
        self.assertIn('data-banner-filter="gantt" class="active"', html)
        self.assertRegex(html, r'id="c1" data-banner-filters="[^"]*" hidden')
        self.assertNotRegex(html, r'id="c2" data-banner-filters="[^"]*" hidden')

    def test_a_selection_that_is_not_a_filter_shows_every_tile(self):
        html = self.render([BannerTile(key='c1', title='A', filter_keys=['crm'])],
                           filters=['crm'], filter_selected='nope')
        self.assertNotIn(' hidden', html)
        self.assertIn('data-banner-filter="" class="active"', html)

    def test_tiles_added_after_the_filters_are_hidden_by_the_selection_too(self):
        card = self.view.add_card('demo', title='Master')
        card.add_banner_tiles([], filters=['crm'], filter_selected='crm')
        card.add_banner_tiles([BannerTile(key='c9', title='Z')])
        self.assertIn('c9', card.extra_card_info['banner_tiles_hidden'])

    def test_no_filters_draws_no_buttons_nor_script(self):
        html = self.render([BannerTile(key='c1', title='A', filter_keys=['crm'])])
        self.assertNotIn('banner-tile-filters', html)
        self.assertNotIn('data-banner-filters', html)

    def test_bad_filter_input_raises(self):
        card = self.view.add_card('demo')
        with self.assertRaises(TypeError):
            card.add_banner_tiles([], filters='crm')
        with self.assertRaises(ValueError):
            card.add_banner_tiles([], filters=[('a', 'b', 'c')])
        with self.assertRaises(ValueError):
            card.add_banner_tiles([], filter_style='buttons')
        with self.assertRaises(TypeError):
            BannerTile(key='c1', filter_keys='crm')

    def test_the_slider_skips_a_hidden_tile_and_its_dot(self):
        html = self.render([BannerTile(key='c1', title='A', filter_keys=['x'])], slider=True, filters=['x'])
        self.assertIn('return !tile.hidden', html)
        self.assertIn("track.dispatchEvent(new Event('scroll'))", html)

    def test_an_image_is_drawn_over_the_banner_so_a_broken_one_leaves_it(self):
        html = self.render([BannerTile(key='c1', title='T', image_url='/i.png', banner_icon='fas fa-cube',
                                       banner_background='#123456')])
        self.assertIn('style="background: #123456"', html)
        self.assertLess(html.index('banner-tile-banner-watermark'), html.index('src="/i.png"'))

    def test_a_banner_caption_takes_the_labels_place(self):
        html = self.render([BannerTile(key='c1', layout='detail', banner_label='Projects',
                                       banner_url='/p/', banner_caption='Preview this course')])
        self.assertIn('Preview this course', html)
        self.assertNotIn('banner-tile-banner-label', html)
