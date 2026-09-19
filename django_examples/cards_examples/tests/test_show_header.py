"""``show_header`` decides whether a card draws a header bar at all.

Three templates guarded it with ``{% if show_header and card.title or card.menu %}``. Django's
``{% if %}`` follows Python's precedence, so ``and`` binds tighter than ``or`` and that reads as
``(show_header and card.title) or card.menu``: a card with a menu drew a header whatever
``show_header`` said, which is most cards. The guard is nested now, since the tag has no
parentheses.

Templates come in two shapes and are asserted separately. ``html``, ``iframe`` and ``treegrid``
ask for a header only when there is something to put in it; ``default``, ``accordion`` and ``table``
draw one whenever ``show_header`` is set. Both must honour ``show_header`` being off. (``message``
is the third shape -- a title is the only thing that earns it a header -- and has its own module,
``test_show_header_message_table``.)

Rendered through ``render_to_string`` with a stand-in card, as ``test_tab_menu_rendered`` is: the
property belongs to the templates, and building each for real wants a treegrid or an iframe url
first.
"""
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

#: Templates whose header needs both the switch and something to show.
NEEDS_CONTENT = ['html', 'iframe', 'treegrid']
#: Templates whose header follows the switch alone.
SWITCH_ONLY = ['default', 'accordion', 'table']
#: The opening tag, not the bare class: several of these templates mention `card-header` in a
#: `<style>` block, which matched a looser check whether or not a header was drawn.
HEADER = '<div class="card-header'


class _Rendered:
    def __init__(self, html=''):
        self.html = html

    @property
    def render(self):
        return mark_safe(self.html)

    def __bool__(self):
        return bool(self.html)


class _Card:
    code = 'probe'
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

    def __init__(self, title='Probe card', menu=''):
        self.title = mark_safe(title) if title else None
        self.menu = _Rendered(menu)
        self.tab_menu = _Rendered('')


def _has_header(template, show_header, title='Probe card', menu=''):
    html = render_to_string(
        f'cards/standard/{template}.html',
        {'card': _Card(title=title, menu=menu), 'card_css_class': 'card',
         'card_body_css_class': 'card-body', 'card_body_css_inner_class': '',
         'card_body_css_outer_class': '', 'show_header': show_header, 'links': [], 'images': []},
    )
    return HEADER in html


MENU = '<div class="btn-group">MENU</div>'


class TestShowHeader(SimpleTestCase):
    def test_a_card_with_a_menu_still_honours_show_header_being_off(self):
        """The bug: the menu alone satisfied the guard and the header came back."""
        for template in NEEDS_CONTENT + SWITCH_ONLY:
            with self.subTest(template=template):
                self.assertFalse(_has_header(template, show_header=False, menu=MENU))

    def test_show_header_off_draws_nothing_without_a_menu_either(self):
        for template in NEEDS_CONTENT + SWITCH_ONLY:
            with self.subTest(template=template):
                self.assertFalse(_has_header(template, show_header=False))

    def test_show_header_on_draws_the_header(self):
        for template in NEEDS_CONTENT + SWITCH_ONLY:
            with self.subTest(template=template):
                self.assertTrue(_has_header(template, show_header=True))

    def test_a_menu_on_its_own_is_enough_to_be_worth_a_header(self):
        for template in NEEDS_CONTENT:
            with self.subTest(template=template):
                self.assertTrue(_has_header(template, show_header=True, title='', menu=MENU))

    def test_nothing_to_show_draws_no_header_where_the_template_asks_for_content(self):
        for template in NEEDS_CONTENT:
            with self.subTest(template=template):
                self.assertFalse(_has_header(template, show_header=True, title=''))
