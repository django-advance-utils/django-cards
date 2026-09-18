"""Every standard body template renders the tab bar the card was given.

A card's tab bar used to depend on which body template it happened to use: seven of the
thirteen rendered ``card.tab_menu``, six did not, and nothing at the call site said which.
The bar is usually the only way off the tab, so a card whose body was one of the six left
the reader stranded -- and consumers worked around it by forking the template.

Rendered here through ``render_to_string`` with a stand-in card rather than through
``CardMixin``: the property under test belongs to the templates themselves, and each of
them otherwise wants its own datatable, treegrid, accordion panels or iframe url before it
will build. A missing context variable renders empty in Django, so a stand-in carrying only
what the header needs is enough to see whether the bar comes out.
"""
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

#: Every template under ``cards/templates/cards/standard`` that draws a whole card.
BODY_TEMPLATES = [
    'accordion', 'card_group', 'datatable', 'default', 'html', 'iframe', 'image_gallery',
    'linked_datatables', 'list_selection', 'message', 'table', 'tree_selection', 'treegrid',
]
TAB_BAR = '<div class="card-tabs">TAB BAR</div>'


class _Rendered:
    """Stands in for an HtmlMenu: something with a ``render`` property and a truth value."""

    def __init__(self, html=''):
        self.html = html

    @property
    def render(self):
        return mark_safe(self.html)

    def __bool__(self):
        return bool(self.html)


class _Card:
    code = 'probe'
    title = mark_safe('Probe card')
    header_icon = None
    header_css_class = ''
    enable_collapse = False
    collapsed = False
    searchable = False
    exportable = False
    ajax_reload = False
    extra_card_info = {}
    child_card_groups = []
    panels = []
    rows = []
    entries = []
    datatable = None

    def __init__(self, tab_menu=TAB_BAR):
        self.menu = _Rendered('<div class="btn-group">MENU</div>')
        self.tab_menu = _Rendered(tab_menu)


def _render(template, card):
    return render_to_string(
        f'cards/standard/{template}.html',
        {'card': card, 'card_css_class': 'card', 'card_body_css_class': 'card-body',
         'card_body_css_inner_class': '', 'card_body_css_outer_class': '',
         'show_header': True, 'links': [], 'images': []},
    )


class TestTabMenuRendered(SimpleTestCase):
    def test_every_body_template_renders_the_tab_bar(self):
        for template in BODY_TEMPLATES:
            with self.subTest(template=template):
                self.assertIn(TAB_BAR, _render(template, _Card()))

    def test_no_template_renders_it_twice(self):
        for template in BODY_TEMPLATES:
            with self.subTest(template=template):
                self.assertEqual(_render(template, _Card()).count(TAB_BAR), 1)

    def test_a_card_with_no_tab_bar_gets_no_markup_for_one(self):
        """The bar is opt-in: a card without one must not grow an empty strip."""
        for template in BODY_TEMPLATES:
            with self.subTest(template=template):
                self.assertNotIn('card-tabs', _render(template, _Card(tab_menu='')))
