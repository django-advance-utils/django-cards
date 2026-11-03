"""add_course_tiles(): a master card whose body is a grid of larger course tiles."""
import re

from django.test import RequestFactory, TestCase
from django.utils.html import format_html
from django.views.generic import TemplateView

from cards.standard import CardMixin, CourseTile


class _CourseCardView(CardMixin, TemplateView):
    pass


class TestCourseTiles(TestCase):
    def setUp(self):
        self.view = _CourseCardView()
        self.view.request = RequestFactory().get('/')

    def render(self, tiles, **kwargs):
        card = self.view.add_card('demo', title='Master')
        card.add_course_tiles(tiles, **kwargs)
        return card.render()

    def test_the_master_card_keeps_its_header(self):
        html = self.render([CourseTile(key='c1', title='Getting Started')])
        self.assertIn('Master', html)
        self.assertIn('django-card__course-tiles', html)
        self.assertIn('id="c1"', html)
        self.assertIn('>Getting Started<', html)

    def test_every_field_reaches_the_tile(self):
        html = self.render([CourseTile(
            key='c1', title='T', description='Desc', banner_label='Projects',
            banner_icon='fas fa-folder', banner_background='#123456', step='Step 1 of 2',
            badge='Required', stats=[('fas fa-play', '13 lessons'), '8 quizzes'],
            progress=30, status='Not started', footer_label='Cat', footer_icon='fas fa-tag',
            action_label='Start', action_url='/start/', css_class='mine')])
        for part in ('course-description', 'course-banner-label', 'course-banner-watermark',
                     'course-step', 'course-badge', 'course-stats', 'course-status',
                     'course-footer', 'django-card__course-tile mine'):
            self.assertIn(part, html)
        self.assertIn('background: #123456', html)
        self.assertIn('width: 30%', html)
        self.assertIn('href="/start/"', html)
        self.assertIn('8 quizzes', html)

    def test_a_tile_draws_only_what_it_was_given(self):
        html = self.render([CourseTile(key='c1', title='T')])
        for part in ('course-description', 'course-step', 'course-badge', 'course-stats',
                     'course-progress', 'course-status', 'course-footer'):
            self.assertNotIn(part, html)

    def test_zero_progress_draws_an_empty_bar(self):
        self.assertIn('width: 0%', self.render([CourseTile(key='c1', title='T', progress=0)]))

    def test_progress_is_clamped(self):
        self.assertIn('width: 100%', self.render([CourseTile(key='c1', title='T', progress=250)]))

    def test_text_fields_are_escaped(self):
        html = self.render([CourseTile(key='c1', title='<script>x</script>',
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
        html = self.render([CourseTile(key='c1', title='T')], width='300px')
        self.assertIn('--django-card-course-tile-width: 300px', html)


class TestCourseTileDetailLayout(TestCase):
    def setUp(self):
        self.view = _CourseCardView()
        self.view.request = RequestFactory().get('/')

    def render(self, tiles):
        card = self.view.add_card('demo', border='none')
        card.add_course_tiles(tiles)
        return card.render()

    def detail(self, **kwargs):
        return CourseTile(key='d1', layout='detail', **kwargs)

    def test_every_detail_part_is_drawn(self):
        html = self.render([self.detail(
            banner_url='/preview/', banner_caption='Preview this course',
            callout_icon='fas fa-route', callout_title='On your path', callout_text='Step 1 of 2.',
            callout_link_label='See your path', callout_link_url='/path/',
            stats=[('fas fa-award', 'Certificate of completion')],
            action_label='Start this course', action_url='/start/',
            secondary_label='Save for later', secondary_url='/save/', note='Saved as you go.')])
        self.assertIn('django-card__course-detail', html)
        self.assertIn('href="/preview/"', html)
        self.assertIn('django-card__course-play', html)
        self.assertIn('Preview this course', html)
        self.assertIn('django-card__course-callout', html)
        self.assertIn('href="/path/"', html)
        self.assertIn('django-card__course-stats--list', html)
        self.assertIn('class="btn btn-primary django-card__course-action"', html)
        self.assertIn('href="/save/"', html)
        self.assertIn('Saved as you go.', html)

    def test_the_detail_button_is_in_the_body_not_a_footer(self):
        html = self.render([self.detail(action_label='Start', action_url='/start/')])
        self.assertNotIn('django-card__course-footer', html)
        self.assertEqual(html.count('href="/start/"'), 1)

    def test_compact_draws_none_of_the_detail_parts(self):
        html = self.render([CourseTile(key='c1', title='T', note='n', secondary_label='s')])
        for part in ('course-detail', 'course-play', 'course-note', 'course-secondary',
                     'course-stats--list'):
            self.assertNotIn(part, html)

    def test_callout_text_is_escaped(self):
        html = self.render([self.detail(callout_title='<b>x</b>', callout_text='<i>y</i>')])
        self.assertNotIn('<b>x</b>', html)
        self.assertNotIn('<i>y</i>', html)

    def test_an_unknown_layout_raises(self):
        with self.assertRaises(ValueError):
            CourseTile(key='x', layout='wide')


class TestCourseTileHighlightLayout(TestCase):
    def setUp(self):
        self.view = _CourseCardView()
        self.view.request = RequestFactory().get('/')

    def render(self, tiles):
        card = self.view.add_card('demo', title='Master')
        card.add_course_tiles(tiles)
        return card.render()

    def test_every_highlight_part_is_drawn(self):
        html = self.render([CourseTile(
            key='p1', layout='highlight', banner_label='Your learning path',
            banner_icon='fas fa-drafting-compass', title='Estimator', description='From call to order.',
            status='0 of 2 steps done', progress=0, action_label='Continue', action_url='/go/')])
        self.assertIn('django-card__course-highlight', html)
        self.assertIn('Your learning path', html)
        self.assertIn('django-card__course-highlight-title', html)
        self.assertIn('0 of 2 steps done', html)
        self.assertIn('django-card__course-highlight-progress', html)
        self.assertIn('class="btn django-card__course-highlight-action"', html)
        self.assertIn('href="/go/"', html)

    def test_highlight_has_no_banner_or_footer(self):
        html = self.render([CourseTile(key='p1', layout='highlight', title='T',
                                       footer_label='x', action_label='Go')])
        self.assertNotIn('django-card__course-banner', html)
        self.assertNotIn('django-card__course-footer', html)

    def test_background_sits_on_the_tile(self):
        html = self.render([CourseTile(key='p1', layout='highlight', title='T',
                                       banner_background='#123456')])
        self.assertIn('id="p1" style="background: #123456"', html)

    def test_it_sits_in_a_grid_beside_compact_tiles(self):
        html = self.render([CourseTile(key='p1', layout='highlight', title='Path'),
                            CourseTile(key='c1', title='Course')])
        self.assertLess(html.index('id="p1"'), html.index('id="c1"'))
        self.assertEqual(len(re.findall(r'django-card__course-tile[ "]', html)), 2)

    def test_highlight_text_is_escaped(self):
        html = self.render([CourseTile(key='p1', layout='highlight', title='<b>x</b>',
                                       banner_label='<i>y</i>')])
        self.assertNotIn('<b>x</b>', html)
        self.assertNotIn('<i>y</i>', html)


class TestCourseTileFeatureAndSlider(TestCase):
    def setUp(self):
        self.view = _CourseCardView()
        self.view.request = RequestFactory().get('/')

    def render(self, tiles, **kwargs):
        card = self.view.add_card('promo', border='none')
        card.add_course_tiles(tiles, **kwargs)
        return card.render()

    def feature(self, key='f1', **kwargs):
        return CourseTile(key=key, layout='feature', title='T', **kwargs)

    def test_feature_with_an_icon_draws_both_shapes_and_the_icon(self):
        html = self.render([self.feature(banner_icon='fas fa-compass', description='D',
                                         action_label='Go', action_url='/go/')])
        self.assertIn('django-card__course-feature-shape--accent', html)
        self.assertIn('django-card__course-feature-shape--grey', html)
        self.assertIn('django-card__course-feature-icon', html)
        self.assertIn('class="btn django-card__course-feature-action"', html)
        self.assertNotIn('django-card__course-feature--plain', html)

    def test_feature_without_an_icon_is_plain(self):
        html = self.render([self.feature()])
        self.assertIn('django-card__course-feature--plain', html)
        self.assertNotIn('django-card__course-feature-shape--accent', html)
        self.assertNotIn('django-card__course-feature-icon', html)

    def test_no_slider_unless_asked(self):
        html = self.render([self.feature()])
        self.assertNotIn('django-card__course-slider', html)
        self.assertNotIn("getElementById('promo_slider')", html)

    def test_slider_has_arrows_a_dot_per_tile_and_its_script(self):
        html = self.render([self.feature('a'), self.feature('b'), CourseTile(key='c', title='C')],
                           slider=True)
        self.assertIn('id="promo_slider"', html)
        self.assertIn('django-card__course-tiles--slider', html)
        self.assertIn('django-card__course-slider-arrow--prev', html)
        self.assertIn('django-card__course-slider-arrow--next', html)
        self.assertEqual(html.count('aria-label="Go to slide'), 3)
        self.assertIn("getElementById('promo_slider')", html)

    def test_feature_text_is_escaped(self):
        html = self.render([CourseTile(key='f', layout='feature', title='<b>x</b>',
                                       description='<i>y</i>')])
        self.assertNotIn('<b>x</b>', html)
        self.assertNotIn('<i>y</i>', html)


class TestCourseTilePlainLayoutAndTitleHtml(TestCase):
    def setUp(self):
        self.view = _CourseCardView()
        self.view.request = RequestFactory().get('/')

    def render(self, tiles):
        card = self.view.add_card('demo', border='none')
        card.add_course_tiles(tiles)
        return card.render()

    def test_plain_draws_title_and_description_only(self):
        html = self.render([CourseTile(key='p', layout='plain', title='Learn',
                                       description='Pick a stage.')])
        self.assertIn('django-card__course-plain-title', html)
        self.assertIn('Pick a stage.', html)
        for part in ('course-banner', 'course-footer', 'course-progress', 'course-plain-action'):
            self.assertNotIn(part, html)

    def test_plain_link(self):
        html = self.render([CourseTile(key='p', layout='plain', title='T',
                                       action_label='All courses', action_url='/all/')])
        self.assertIn('class="django-card__course-plain-action"', html)
        self.assertIn('href="/all/"', html)

    def test_title_html_is_rendered_as_markup(self):
        html = self.render([CourseTile(key='p', layout='plain',
                                       title_html=format_html('Learn <em>every</em> part of {}', 'X'))])
        self.assertIn('Learn <em>every</em> part of X', html)

    def test_format_html_still_escapes_what_goes_into_title_html(self):
        html = self.render([CourseTile(key='p', layout='plain',
                                       title_html=format_html('<em>{}</em>', '<script>x</script>'))])
        self.assertNotIn('<script>x', html)

    def test_plain_title_is_escaped(self):
        html = self.render([CourseTile(key='p', layout='plain', title='<em>x</em>')])
        self.assertNotIn('<em>x</em>', html)

    def test_title_html_works_in_every_layout(self):
        for layout in ('compact', 'detail', 'highlight', 'feature', 'plain'):
            with self.subTest(layout=layout):
                html = self.render([CourseTile(key='p', layout=layout,
                                               title_html=format_html('<em>{}</em>', 'hi'))])
                self.assertIn('<em>hi</em>', html)


class TestCourseTileShowcaseLayout(TestCase):
    def setUp(self):
        self.view = _CourseCardView()
        self.view.request = RequestFactory().get('/')

    def render(self, tiles):
        card = self.view.add_card('demo', border='none')
        card.add_course_tiles(tiles)
        return card.render()

    def showcase(self, **kwargs):
        return CourseTile(key='s', layout='showcase', title='Fits together', **kwargs)

    def test_every_showcase_part_is_drawn(self):
        html = self.render([self.showcase(
            description='One map.', points=[('fas fa-cubes', 'Every area'), ('fas fa-cog', 'Settings', '#123456')],
            banner_icon='fas fa-project-diagram', flow=['CRM', 'Projects', 'Gantt'],
            panel_icon='fas fa-cog', action_label='Open the map', action_url='/map/')])
        self.assertIn('django-card__course-showcase-points', html)
        self.assertIn('Every area', html)
        self.assertIn('background: #e3cde6', html)   # the first default colour
        self.assertIn('background: #123456', html)   # a point's own colour
        self.assertIn('django-card__course-showcase-panel--main', html)
        self.assertEqual(html.count('django-card__course-showcase-flow-node'), 3)
        self.assertEqual(html.count('django-card__course-showcase-flow-line'), 2)
        self.assertIn('django-card__course-showcase-panel--icon', html)
        self.assertIn('class="btn django-card__course-showcase-action"', html)
        self.assertIn('href="/map/"', html)
        self.assertNotIn('django-card__course-showcase--text-only', html)

    def test_no_panels_means_text_only(self):
        html = self.render([self.showcase()])
        self.assertIn('django-card__course-showcase--text-only', html)
        self.assertNotIn('django-card__course-showcase-panels', html)

    def test_only_the_panels_given_are_drawn(self):
        html = self.render([self.showcase(flow=['A', 'B'])])
        self.assertIn('django-card__course-showcase-panel--flow', html)
        self.assertNotIn('django-card__course-showcase-panel--main', html)
        self.assertNotIn('django-card__course-showcase-panel--icon', html)

    def test_showcase_text_is_escaped(self):
        html = self.render([self.showcase(points=[('fas fa-cog', '<b>p</b>')], flow=['<i>f</i>'])])
        self.assertNotIn('<b>p</b>', html)
        self.assertNotIn('<i>f</i>', html)

    def test_a_malformed_point_raises(self):
        with self.assertRaises(ValueError):
            self.render([self.showcase(points=['just text'])])
