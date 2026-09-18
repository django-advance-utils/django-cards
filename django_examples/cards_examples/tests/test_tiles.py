"""add_tiles(): a card body that is a grid of small tiles, one per object.

The cases worth holding are the escaping contract -- one field rendered as markup and every
other field escaped -- the per-card tile width, and the parts of a tile that are drawn only
when they were given.
"""
from django.test import RequestFactory, TestCase
from django.utils.html import format_html
from django.views.generic import TemplateView

from cards.standard import CardMixin, Tile


class _TileCardView(CardMixin, TemplateView):
    def build(self, tiles, **kwargs):
        card = self.add_card('demo', title='Demo')
        card.add_tiles(tiles, **kwargs)
        return card


class TestTiles(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = _TileCardView()
        self.view.request = self.factory.get('/')

    def render(self, tiles, **kwargs):
        return self.view.build(tiles, **kwargs).render()

    def test_a_tile_renders_its_heading_and_key(self):
        html = self.render([Tile(key='tile_1', heading='Brass')])
        self.assertIn('django-card__tiles', html)
        self.assertIn('id="tile_1"', html)
        self.assertIn('>Brass<', html)

    def test_every_field_reaches_the_tile(self):
        html = self.render([Tile(key='tile_1', heading='Brass', subheading='Satin',
                                 meta=['£3.00'], image_url='/media/satin.jpg',
                                 badge='Default', edit_url='/edit/1/', tooltip='Brass / Satin',
                                 css_class='my-tile')])
        self.assertIn('django-card__tile-heading', html)
        self.assertIn('django-card__tile-subheading', html)
        self.assertIn('django-card__tile-meta', html)
        self.assertIn('src="/media/satin.jpg"', html)
        self.assertIn('django-card__tile-badge', html)
        self.assertIn('href="/edit/1/"', html)
        self.assertIn('title="Brass / Satin"', html)
        self.assertIn('django-card__tile my-tile', html)

    def test_a_tile_draws_only_what_it_was_given(self):
        # Each part is optional, and an absent one leaves nothing behind -- otherwise a tile
        # with only a heading would carry the height of the empty blocks under it.
        html = self.render([Tile(key='tile_1', heading='Brass')])
        self.assertNotIn('django-card__tile-subheading', html)
        self.assertNotIn('django-card__tile-meta', html)
        self.assertNotIn('django-card__tile-image', html)
        self.assertNotIn('django-card__tile-badge', html)
        self.assertNotIn('django-card__tile-edit', html)
        self.assertNotIn('title=', html.split('django-card__tile"')[1][:200])


class TestTileEscaping(TestCase):
    """The one thing this card must not get wrong.

    A heading that is markup and a heading that is tenant-entered text go through different
    fields on purpose, so that passing data into the markup one is an obvious mistake rather
    than an invisible one.
    """

    def setUp(self):
        self.view = _TileCardView()
        self.view.request = RequestFactory().get('/')

    def render(self, tiles, **kwargs):
        card = self.view.add_card('demo', title='Demo')
        card.add_tiles(tiles, **kwargs)
        return card.render()

    def test_heading_is_escaped(self):
        html = self.render([Tile(key='t', heading='<script>alert(1)</script>')])
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)

    def test_subheading_meta_badge_and_tooltip_are_escaped(self):
        html = self.render([Tile(key='t',
                                 subheading='<b>sub</b>',
                                 meta=['<b>meta</b>', ('<b>pair</b>', 'text-danger')],
                                 badge='<b>badge</b>',
                                 tooltip='<b>tip</b>')])
        self.assertNotIn('<b>', html)
        for value in ('sub', 'meta', 'pair', 'badge', 'tip'):
            self.assertIn(f'&lt;b&gt;{value}&lt;/b&gt;', html)

    def test_heading_html_is_rendered_as_markup(self):
        # The field that is markup by name: a swatch carrying an inline background colour.
        html = self.render([Tile(key='t', heading_html='<span style="background:#b5a642">Brass</span>')])
        self.assertIn('<span style="background:#b5a642">Brass</span>', html)

    def test_heading_html_does_not_unescape_the_name_inside_it(self):
        # The block is markup; the name in it is still the tenant's. format_html escapes the
        # name, and nothing in the template undoes that.
        heading = format_html('<span style="background:{}">{}</span>',
                              '#b5a642', '<script>alert(1)</script>')
        html = self.render([Tile(key='t', heading_html=heading)])
        self.assertIn('<span style="background:#b5a642">', html)
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)

    def test_heading_html_wins_over_heading(self):
        html = self.render([Tile(key='t', heading='plain', heading_html='<i>markup</i>')])
        self.assertIn('<i>markup</i>', html)
        self.assertNotIn('plain', html)

    def test_a_heading_that_looks_like_markup_stays_text(self):
        # Passing markup to `heading` does not quietly render it: the escaping follows the
        # field the caller chose, not the shape of the value.
        html = self.render([Tile(key='t', heading='<span style="background:red">Brass</span>')])
        self.assertNotIn('<span style="background:red">', html)
        self.assertIn('&lt;span', html)


class TestTileWidth(TestCase):
    def setUp(self):
        self.view = _TileCardView()
        self.view.request = RequestFactory().get('/')

    def test_width_reaches_the_container_as_a_custom_property(self):
        # Per card, not fixed in the stylesheet: a tile holding a two-part measurement must
        # not wrap, and one holding a colour name need not be as wide.
        html = self.view.build([Tile(key='t', heading='838 mm')], width='190px').render()
        self.assertIn('style="--django-card-tile-width: 190px"', html)

    def test_no_property_without_a_width(self):
        html = self.view.build([Tile(key='t', heading='Brass')]).render()
        self.assertNotIn('--django-card-tile-width', html)


class TestTileMeta(TestCase):
    def test_a_plain_string_line_carries_no_class(self):
        self.assertEqual(Tile(key='t', meta=['£3.00']).meta_lines,
                         [{'text': '£3.00', 'css_class': ''}])

    def test_a_pair_carries_its_class(self):
        self.assertEqual(Tile(key='t', meta=[('none in stock', 'text-danger')]).meta_lines,
                         [{'text': 'none in stock', 'css_class': 'text-danger'}])

    def test_a_malformed_pair_is_rejected(self):
        # Loudly, rather than by silently dropping the class or the text.
        with self.assertRaises(ValueError):
            Tile(key='t', meta=[('a', 'b', 'c')]).meta_lines

    def test_meta_defaults_to_no_lines(self):
        self.assertEqual(Tile(key='t').meta_lines, [])


class TestTileBuild(TestCase):
    def test_a_dict_is_accepted(self):
        self.assertEqual(Tile.build({'key': 't', 'heading': 'Brass'}), Tile(key='t', heading='Brass'))

    def test_a_tile_is_passed_through(self):
        tile = Tile(key='t')
        self.assertIs(Tile.build(tile), tile)

    def test_a_misspelled_dict_key_is_rejected(self):
        # Rather than rendering a tile with the field quietly missing.
        with self.assertRaises(TypeError):
            Tile.build({'key': 't', 'headnig': 'Brass'})

    def test_anything_else_is_rejected(self):
        with self.assertRaises(TypeError):
            Tile.build('Brass')


class TestTilesEmptyState(TestCase):
    def setUp(self):
        self.view = _TileCardView()
        self.view.request = RequestFactory().get('/')

    def test_the_empty_message_shows_when_there_are_no_tiles(self):
        html = self.view.build([], empty_message='No colours yet.').render()
        self.assertIn('django-card__tiles-empty', html)
        self.assertIn('No colours yet.', html)

    def test_the_empty_message_is_escaped(self):
        html = self.view.build([], empty_message='<b>none</b>').render()
        self.assertNotIn('<b>none</b>', html)

    def test_nothing_is_drawn_without_an_empty_message(self):
        html = self.view.build([]).render()
        self.assertIn('django-card__tiles', html)
        self.assertNotIn('django-card__tiles-empty', html)

    def test_the_empty_message_goes_once_there_are_tiles(self):
        html = self.view.build([Tile(key='t', heading='Brass')],
                               empty_message='No colours yet.').render()
        self.assertNotIn('No colours yet.', html)


class TestTilesCardWiring(TestCase):
    def setUp(self):
        self.view = _TileCardView()
        self.view.request = RequestFactory().get('/')

    def test_the_stylesheet_is_emitted_for_a_tile_card(self):
        # The chrome lives in cards.css, so a tile card has to bring it whether or not it
        # also asked for a border -- until now only `border` pulled the stylesheet in.
        html = self.view.build([Tile(key='t', heading='Brass')]).render()
        self.assertIn('cards/css/cards.css', html)

    def test_the_stylesheet_is_emitted_once_for_a_page_of_tile_cards(self):
        response = self.client.get('/tiles/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode().count('cards/css/cards.css'), 1)

    def test_calling_add_tiles_again_adds_to_the_grid(self):
        card = self.view.add_card('demo', title='Demo')
        card.add_tiles([Tile(key='a', heading='Brass')])
        card.add_tiles([Tile(key='b', heading='Chrome')])
        html = card.render()
        self.assertIn('id="a"', html)
        self.assertIn('id="b"', html)

    def test_add_tiles_returns_the_card(self):
        card = self.view.add_card('demo', title='Demo')
        self.assertIs(card.add_tiles([]), card)

    def test_the_card_keeps_its_header_and_menu(self):
        card = self.view.add_card('demo', title='Colours', menu=[('cards_examples:tiles', 'Add')])
        card.add_tiles([Tile(key='t', heading='Brass')])
        html = card.render()
        self.assertIn('Colours', html)
        self.assertIn('card-header', html)
        self.assertIn('Add', html)

    def test_a_titleless_card_draws_no_header(self):
        card = self.view.add_card('demo')
        card.add_tiles([Tile(key='t', heading='Brass')])
        self.assertNotIn('card-header', card.render())


class TestTilesExamplePage(TestCase):
    def test_the_example_page_renders_every_case(self):
        response = self.client.get('/tiles/')
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        # every field, heading only, both consumer shapes, and the empty state
        self.assertIn('Every field', html)
        self.assertIn('Heading only', html)
        # the card title is mark_safe'd by CardBase, so the ampersand stays raw
        self.assertIn('Colours & Finishes (heading_html)', html)
        self.assertIn('Sizes (wider tile, plain heading)', html)
        self.assertIn('No tiles yet. Use Add above to add one.', html)
        # the wider tile is per card: the sizes card asks for 190px, the colours card 150px
        self.assertIn('--django-card-tile-width: 190px', html)
        self.assertIn('--django-card-tile-width: 150px', html)
        # the escaping is visible in the output: the swatch is markup, the name inside is not
        self.assertIn('<span style="background:#b5a642;color:#000;padding:4px 6px;border-radius:3px">', html)
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
