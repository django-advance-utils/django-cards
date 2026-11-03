import _string
import datetime
import json
import math
import re
import string
from html import unescape
from dataclasses import dataclass, field

from ajax_helpers.html_include import pip_version
from ajax_helpers.utils import random_string
from django.core.exceptions import FieldDoesNotExist
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils.html import conditional_escape, strip_tags
from django.utils.safestring import mark_safe
from django.utils.timesince import timesince
from django.utils.text import slugify
from django_datatables.columns import ColumnBase
from django_datatables.datatables import DatatableTable
from django_datatables.plugins.reorder import Reorder
from django_datatables.reorder_datatable import OrderedDatatable
from django_menus.menu import HtmlMenu

from cards.packs import pack_class, resolve_template
from cards.render_scope import get_render_scope


def json_for_script(value):
    """json.dumps hardened for embedding inside a <script> element.

    These blobs reach the page through mark_safe, so the JSON text itself must not be able
    to close the script element or open a tag: a node title containing '</script>' would
    otherwise end the script mid-JSON and hand the rest of the value to the HTML parser.
    The escapes are ordinary JSON string escapes, so json.loads and a JS engine both read
    back the original characters. The templates splice this text into the script as a JavaScript
    literal, not through JSON.parse; json.dumps's default ensure_ascii escapes U+2028 and U+2029,
    which older engines would otherwise read as line breaks inside that literal.
    """
    return (json.dumps(value)
            .replace('<', '\\u003c')
            .replace('>', '\\u003e')
            .replace('&', '\\u0026'))


#: The digits of a css hex colour: 3, 4, 6 or 8 of them (#rgb, #rgba, #rrggbb, #rrggbbaa).
HEX_COLOUR_DIGITS = r'(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})'

#: The functions a colour may be built from. Anything else is refused -- ``url()``,
#: ``image-set()`` and ``element()`` reach for something off the page, and ``expression()`` runs.
_COLOUR_FUNCTIONS = frozenset({
    'rgb', 'rgba', 'hsl', 'hsla', 'hwb', 'lab', 'lch', 'oklab', 'oklch', 'color', 'color-mix',
    'light-dark', 'var', 'calc',
})
#: Every character a colour may hold. No semicolon, colon, quote, backslash, brace or angle bracket,
#: so nothing can end the declaration, start another, or leave the attribute.
_COLOUR_CHARS = re.compile(r'[0-9A-Za-z#.,%/+\- ()_]+')
_COLOUR_TOKEN = re.compile(r'([A-Za-z][A-Za-z0-9-]*)?\(|\)| ')


#: A ``background`` may also be a gradient, as a banner's is documented to be.
_BACKGROUND_FUNCTIONS = _COLOUR_FUNCTIONS | frozenset({
    'linear-gradient', 'radial-gradient', 'conic-gradient',
    'repeating-linear-gradient', 'repeating-radial-gradient', 'repeating-conic-gradient',
})


def css_background(background):
    """``background`` when it is safe to write into a ``style`` as a ``background``, else ``None``.

    :func:`_checked_css`'s rules, with the gradient functions allowed as well, and the shorthand's
    other parts: layers side by side (``linear-gradient(...), linear-gradient(...)``) and the
    position, size and repeat keywords (``#e6f0fb center / cover no-repeat``). Still no ``url()``:
    a banner image has a field of its own.
    """
    return _checked_css(background, _BACKGROUND_FUNCTIONS, single=False, max_length=500)


def css_colour(colour):
    """``colour`` when it is one css colour that is safe to write into a ``style``, else ``None``.

    :func:`_checked_css`'s rules, as a single value: a name (``green``, ``currentColor``), ``#``
    and hex digits, or one of `_COLOUR_FUNCTIONS` -- nested, with a fallback, in modern syntax:
    ``var(--ok, green)``, ``rgb(var(--r) 0 0)``, ``oklch(70% 0.1 150)``,
    ``color-mix(in srgb, red, blue)``. Not a gradient: that is a background, not a colour.
    """
    return _checked_css(colour, _COLOUR_FUNCTIONS, single=True, max_length=200)


def _checked_css(value, functions, single, max_length):
    """``value`` if it is safe to write into a ``style`` attribute as a property's value, else ``None``.

    A value handed to a card is printed inside ``style="..."``, where html-escaping is the wrong
    tool: the character that does the damage is a semicolon, and escaping leaves it alone, so a
    stored ``red;position:fixed;inset:0`` would arrive as more declarations and lift the element
    over the page. So the shape is checked instead, and anything else dropped, which a template
    draws as no value at all.

    The rules: only `_COLOUR_CHARS` (nothing that can end the declaration, start another or
    leave the attribute); every function one of ``functions``, its brackets balanced, a ``var()``
    naming a custom property; every ``#`` followed by 3, 4, 6 or 8 hex digits. With ``single``,
    one value and no more -- a name, a hex colour or one function -- as a colour is. No longer
    than ``max_length``, so a stored value cannot make the check, or the page, carry an essay.
    Checked for
    safety rather than validity: a malformed value that gets through is one the browser ignores.
    """
    if value is None:
        return None
    value = str(value).strip()
    if not value or len(value) > max_length or not _COLOUR_CHARS.fullmatch(value):
        return None
    if not all(re.fullmatch(HEX_COLOUR_DIGITS, digits) for digits in re.findall(r'#([0-9A-Za-z]*)', value)):
        return None
    if '(' not in value and ')' not in value:
        if single:
            return value if re.fullmatch('#' + HEX_COLOUR_DIGITS + '|[A-Za-z]+', value) else None
        return value
    depth = 0
    for match in _COLOUR_TOKEN.finditer(value):
        token = match.group(0)
        if token == ' ':
            if single and depth == 0:  # two values side by side, not one colour
                return None
        elif token == ')':
            depth -= 1
            if depth < 0:
                return None
        else:
            name = (match.group(1) or '').lower()
            if name not in functions:
                return None
            if name == 'var' and not value[match.end():].lstrip().startswith('--'):
                return None
            depth += 1
    if depth or (single and not value.endswith(')')):
        return None
    return value


def _is_percentage(value):
    """Whether ``value`` reads as a finite number, as a progress bar's width must."""
    try:
        return math.isfinite(float(str(value).strip()))
    except (TypeError, ValueError):
        return False


def escape_value(value):
    """`value` as ``{{ value }}`` prints it: escaped, unless it is marked safe.

    A row's value and label are text unless they say otherwise. Markup handed to a card has
    to be marked safe where it is made -- ``mark_safe``, ``format_html``, a rendered template
    or menu -- and everything else is escaped, both where the templates print a row and
    where the card builds markup around a value itself (``html_override``, a row style, the
    many-to-many badges, a merged row). Anything that is not a string is ``str()``'d first,
    as the template engine does, so an object whose ``__str__`` returns safe markup (an
    html_classes element) is still markup.
    """
    if not isinstance(value, str):
        value = str(value)
    return conditional_escape(value)


class _RowStyleFormatter(string.Formatter):
    """Fills a row style's placeholders, each one as ``{{ }}`` would print it.

    A row style is the caller's markup with ``{value}``, ``{label}`` and the like in it. The
    markup is trusted; what fills it is escaped unless it is marked safe, and so is anything
    looked up on it -- ``{value[v1]}`` on a dict value, ``{value.name}`` on an object. A
    placeholder nothing fills reads as empty.

    An attribute whose name starts with an underscore is never looked up, and reads as empty
    too. The style is a format string, so text written into it -- rather than put in a
    placeholder -- is handed the format mini-language, and ``{label.__init__.__globals__}``
    walks from a value to module globals and on to settings.
    """

    def get_value(self, key, args, kwargs):
        return kwargs.get(key, '')

    def get_field(self, field_name, args, kwargs):
        first, rest = _string.formatter_field_name_split(field_name)
        obj = self.get_value(first, args, kwargs)
        for is_attribute, key in rest:
            if is_attribute:
                if key.startswith('_'):
                    return '', first
                obj = getattr(obj, key)
            else:
                obj = obj[key]
        return obj, first

    def format_field(self, value, format_spec):
        if not format_spec:
            return escape_value(value)
        # A spec pads or cuts, so it goes on the text before that is escaped -- after, it
        # could cut an entity in half -- and on markup as it stands.
        text = value if isinstance(value, str) else str(value)
        formatted = format(text, format_spec)
        return mark_safe(formatted) if hasattr(text, '__html__') else escape_value(formatted)


_row_style_formatter = _RowStyleFormatter()


class _MenuWrapper:
    """Decorates a menu, passing every attribute read, write and delete through to it.

    So a wrapper is a drop-in wherever the menu was: forwarding reads alone holds only until
    something assigns to it -- the value lands on the wrapper, reads back off the wrapper, and the
    menu never sees it (``compare_full_path`` set on a wrapped tab menu was lost that way, and no
    tab came back active). The names in ``_OWN`` are the wrapper's own.
    """

    _OWN = frozenset({'_menu'})

    def __init__(self, html_menu):
        object.__setattr__(self, '_menu', html_menu)

    def __getattr__(self, name):
        # Only reached for a name the wrapper does not have. One of its own missing means the
        # instance is being built without __init__ -- copy, deepcopy and unpickle all do -- and
        # reading `_menu` here would come straight back, forever.
        if name in self._OWN:
            raise AttributeError(name)
        return getattr(self._menu, name)

    def __setattr__(self, name, value):
        if name in self._OWN:
            object.__setattr__(self, name, value)
        else:
            setattr(self._menu, name, value)

    def __delattr__(self, name):
        if name in self._OWN:
            object.__delattr__(self, name)
        else:
            delattr(self._menu, name)


def visible_menu_items(menu):
    """The items of ``menu`` that will be drawn, decided as django-menus decides when it renders.

    ``test_visible(request)`` is what ``HtmlMenu.render`` asks of each item: it resolves a callable
    ``visible`` and, for a link, the target view's ``view_permission`` and the current view's
    ``menu_permissions``. An item without it (a stand-in) is read by its ``visible`` alone.
    """
    request = getattr(menu, 'request', None)
    items = []
    for item in getattr(menu, 'menu_items', None) or ():
        if hasattr(item, 'test_visible'):
            visible = item.test_visible(request) and item.visible
        else:
            visible = getattr(item, 'visible', True)
        if visible:
            items.append(item)
    return items


class TabMenuWithSubRow(_MenuWrapper):
    """A card's tab bar with a second, quieter row of tabs under it.

    For a group of pages under a top tab (Summary, Items, Money... and under Summary its own
    Summary and Settings). A card carries one ``tab_menu``, which every card template prints, so
    this renders both rows from that one slot: the top menu as it is, then the sub menu in a
    ``django-card__sub-tabs`` row styled in ``cards.css``. It composes with
    :class:`ScrollableTabMenu`, which then holds the top row only.

    Whether the second row is drawn is decided when it renders, as django-menus decides which
    tabs to draw: only when the top row shows a tab and the sub row shows two or more. A single
    sub tab repeats the top tab it sits under and is noise; and a tab hidden by ``visible`` or a
    view's permissions, or one added to the menu after the card was built, counts as it will draw.

    Reads pass to the top menu; a setting written through it (``compare_full_path``) is written to
    both rows, so the two match the url the same way; ``sub_menu`` reads and replaces the second.
    """

    _OWN = _MenuWrapper._OWN | {'_sub_menu'}

    def __init__(self, html_menu, sub_menu):
        super().__init__(html_menu)
        object.__setattr__(self, '_sub_menu', sub_menu)

    @property
    def sub_menu(self):
        return self._sub_menu

    def __setattr__(self, name, value):
        if name == 'sub_menu':
            object.__setattr__(self, '_sub_menu', value)
        elif name in self._OWN:
            object.__setattr__(self, name, value)
        else:
            setattr(self._menu, name, value)
            setattr(self._sub_menu, name, value)

    def __delattr__(self, name):
        if name in self._OWN:
            object.__delattr__(self, name)
        else:
            delattr(self._menu, name)
            if hasattr(self._sub_menu, name):
                delattr(self._sub_menu, name)

    def render(self):
        top = self._menu.render()
        if not visible_menu_items(self._menu) or len(visible_menu_items(self._sub_menu)) < 2:
            return top
        return mark_safe(f'{top}<div class="django-card__sub-tabs">{self._sub_menu.render()}</div>')


class ScrollableTabMenu(_MenuWrapper):
    """
    Wraps an HtmlMenu tab menu to add left/right scroll buttons when tabs overflow.

    Drop-in replacement for the HtmlMenu assigned to card.tab_menu. All attribute
    access falls through to the underlying menu so existing code is unaffected.
    The scroll buttons are hidden when not needed and update automatically on resize.

    Usage — pass ``scrollable_tab_menu=True`` to ``add_card()`` or any convenience
    method that accepts ``**kwargs`` (e.g. ``add_treegrid_card``).
    """

    def render(self):
        inner = self._menu.render()
        uid = 'stm_' + random_string()
        css_url = static('cards/scrollable_tab_menu/scrollable_tab_menu.css')
        js = (
            "(function(){"
            f"var c=document.getElementById('{uid}');"
            "function i(c){"
            "var w=c.querySelector('.stm__wrapper'),"
            "u=w&&w.querySelector('ul'),"
            "l=c.querySelector('.stm__btn--left'),"
            "r=c.querySelector('.stm__btn--right');"
            "if(!w||!u||!l||!r)return;"
            "function p(){"
            "var o=u.scrollWidth>u.clientWidth+1;"
            "l.classList.toggle('stm__btn--visible',o&&u.scrollLeft>0);"
            "r.classList.toggle('stm__btn--visible',o&&u.scrollLeft+u.clientWidth<u.scrollWidth-1);}"
            "l.addEventListener('click',function(){u.scrollBy({left:-120,behavior:'smooth'});});"
            "r.addEventListener('click',function(){u.scrollBy({left:120,behavior:'smooth'});});"
            # Open showing the active tab. A card re-rendered over ajax gets a new bar scrolled to
            # the start, so a tab reached by scrolling right was off screen the moment it was
            # picked. Centred rather than put at an edge, so a button that appears once it
            # scrolls cannot cover it. Scrolling shows or hides the buttons, which changes the
            # strip's width, so it is measured again after each move; a few passes settle it.
            # Done once the strip overflows and has been placed. Until then (a bar in a hidden
            # tab pane or modal measures 0; one inserted before its stylesheet applies has not
            # yet stopped wrapping) it is tried again from the ResizeObserver. The strip's own
            # scrollLeft is set rather than scrollIntoView, which would scroll the page too.
            "var a=u.querySelector('.nav-link.active,.active>.nav-link'),d=!a;"
            "function s(){"
            "if(d||!u.clientWidth||u.scrollWidth<=u.clientWidth+1)return;"
            "for(var n=0;n<3;n++){var ar=a.getBoundingClientRect(),ur=u.getBoundingClientRect();"
            "if(ar.left>=ur.left-1&&ar.right<=ur.right+1)break;"
            "u.scrollLeft+=ar.left-ur.left-(u.clientWidth-ar.width)/2;p();}"
            "d=true;}"
            "u.addEventListener('scroll',p);"
            "if(window.ResizeObserver)new ResizeObserver(function(){p();s();}).observe(w);"
            "p();s();"
            "}"
            "if(c)i(c);"
            "else document.addEventListener('DOMContentLoaded',function(){"
            f"var c=document.getElementById('{uid}');if(c)i(c);}});"
            "})();"
        )
        return mark_safe(
            f'<link rel="stylesheet" href="{css_url}">'
            f'<div class="stm" id="{uid}">'
            f'<button class="stm__btn stm__btn--left" tabindex="-1" aria-label="Scroll tabs left">'
            f'<i class="fas fa-chevron-left"></i></button>'
            f'<div class="stm__wrapper">{inner}</div>'
            f'<button class="stm__btn stm__btn--right" tabindex="-1" aria-label="Scroll tabs right">'
            f'<i class="fas fa-chevron-right"></i></button>'
            f'</div>'
            f'<script>{js}</script>'
        )


CARD_TYPE_STANDARD = 1
CARD_TYPE_DATATABLE = 2
CARD_TYPE_ORDERED_DATATABLE = 3
CARD_TYPE_HTML = 4
CARD_TYPE_LIST_SELECTION = 5
CARD_TYPE_CARD_GROUP = 6
CARD_TYPE_CARD_LAYOUT = 7
CARD_TYPE_CARD_MESSAGE = 8
CARD_TYPE_LINKED_DATATABLES = 9
CARD_TYPE_ACCORDION = 10
CARD_TYPE_PANEL_LAYOUT = 11
CARD_TYPE_IFRAME = 12
CARD_TYPE_TREEGRID = 13

# Opt-in card chrome. None keeps the Bootstrap `.card` border; 'thin' is a 1px
# hairline like the purchase-order detail boxes; 'none' drops the box entirely
# so a card can be just icons (or any other content) sitting on the page.
CARD_BORDER_THIN = 'thin'
CARD_BORDER_NONE = 'none'
CARD_BORDER_CSS_CLASSES = {
    CARD_BORDER_THIN: 'django-card--thin-border',
    CARD_BORDER_NONE: 'django-card--borderless',
}
CARD_CSS_MARK = '_django_cards_css_rendered'
# The stylesheet is injected by hand rather than through lib_include, so it has to carry
# its own cache-buster: without one a browser holding the previous release's copy styles
# this release's markup, which is worse than having no stylesheet at all. Same ?v= the
# sibling libraries put on theirs.
CARD_CSS_VERSION_QS = f'?v={pip_version("django-cards")}'


def normalize_card_border(border):
    """Map add_card(border=...) to 'thin', 'none', or None (default chrome).

    A caller flipping the option from a flag can have that flag either way round, so
    False/0 (and 'false'/'off'/'0') mean "no chrome at all" while True/1 (and
    'true'/'on'/'1') mean "whatever the default chrome is" -- the same answer as None.
    """
    if border is None or border == 'default':
        return None
    if border is False or border == 0:
        return CARD_BORDER_NONE
    if border is True or border == 1:
        return None
    if isinstance(border, str):
        value = border.lower().strip()
        if value in ('none', 'off', 'false', '0'):
            return CARD_BORDER_NONE
        if value == CARD_BORDER_THIN:
            return CARD_BORDER_THIN
        if value in ('default', 'true', 'on', '1'):
            return None
    raise ValueError(
        f"Unknown card border {border!r}. Use None, True, 'thin', or 'none'."
    )


def card_css_once(request=None):
    """The shared card stylesheet, emitted once per request when a bordered card renders.

    Falls back to the request when there is no render scope, matching the treegrid
    shared-asset tag: outside a request cycle there is nothing to mark, and carrying a
    second copy of a stylesheet the browser has already cached beats a page with none.
    """
    holder = get_render_scope() or request
    if holder is not None and getattr(holder, CARD_CSS_MARK, False):
        return ''
    html = render_to_string('cards/standard/_card_css.html',
                            {'card_css_version_qs': CARD_CSS_VERSION_QS})
    if holder is not None:
        setattr(holder, CARD_CSS_MARK, True)
    return html


@dataclass
class Tile:
    """One tile in an :meth:`CardBase.add_tiles` grid -- a small card standing for one object.

    Every field but ``key`` is optional, and a tile draws only the parts it was given::

        Tile(key='colour_finish_12', heading='Brass', subheading='Satin',
             meta=['£3.00', ('none in stock', 'text-danger')],
             image_url='/media/finishes/satin.jpg', badge='Default',
             edit_url="javascript:django_modal.show_modal('colour_finish_modal-12')",
             tooltip='Brass / Satin')

    Args:
        key (str): Stable identifier for this tile; becomes the tile's DOM id, so it has to
            be unique on the page. Usually the object's pk with a prefix.
        heading (str, optional): The tile's first line. Escaped.
        heading_html (str, optional): The tile's first line as markup, for a heading that is
            built rather than written -- a swatch carrying an inline background colour, say.
            Rendered unescaped; see the warning below. Used instead of ``heading``, not
            alongside it: pass one or the other.
        subheading (str, optional): A second, quieter line under the heading. Escaped.
        meta (list, optional): Short lines under the heading -- a price, a stock figure. Each
            entry is either a string or a ``(text, css_class)`` pair when the line needs a
            class of its own (``'text-danger'`` on an out-of-stock line, say). Escaped.
        image_url (str, optional): A thumbnail drawn under the meta lines.
        badge (str, optional): A flag drawn last, in a Bootstrap badge. Escaped.
        edit_url (str, optional): Where the pencil in the tile's top-right corner goes. No
            pencil is drawn without one. A plain href, so a ``javascript:`` URL that opens a
            modal works as well as a real one.
        tooltip (str, optional): The tile's ``title``, and the alt text of its image. Escaped.
        css_class (str, optional): Extra classes on the tile, for whatever only this caller
            styles.

    Warning:
        ``heading_html`` is the one field rendered as-is; everything else is escaped by the
        template. It is named for what it does so that putting user-entered text through it
        is an obvious mistake rather than an invisible one. Build it with
        :func:`~django.utils.html.format_html` (or escape the parts yourself) and never pass
        a value that came from a form or a model field straight into it.
    """

    key: str
    heading: str = None
    heading_html: str = None
    subheading: str = None
    meta: list = field(default_factory=list)
    image_url: str = None
    badge: str = None
    edit_url: str = None
    tooltip: str = None
    css_class: str = None

    @classmethod
    def build(cls, tile):
        """Return `tile` as a Tile, accepting a dict of the same fields for convenience.

        A dict goes through the constructor rather than being used as-is, so a misspelled key
        raises here instead of quietly rendering a tile with the field missing.
        """
        if isinstance(tile, cls):
            return tile
        if isinstance(tile, dict):
            return cls(**tile)
        raise TypeError(f'add_tiles() takes Tile objects or dicts of Tile fields, not '
                        f'{type(tile).__name__}')

    @property
    def meta_lines(self):
        """`meta` as {'text', 'css_class'} dicts.

        Normalised here rather than in the template because a template cannot tell a bare
        string from a (text, css_class) pair without a filter to do it.
        """
        lines = []
        for line in self.meta or ():
            if isinstance(line, (list, tuple)):
                if len(line) != 2:
                    raise ValueError(f'A meta line pair is (text, css_class); got {line!r}')
                text, css_class = line
            else:
                text, css_class = line, None
            lines.append({'text': text, 'css_class': css_class or ''})
        return lines


class CardSection:
    """One folding section of an :meth:`CardBase.add_sections` stack: a card under a header.

    The header is a toggle holding the section's title (and the card's ``header_icon``) and a
    chevron, with the card's own header controls beside it -- its menu, search box, export and
    reload buttons -- never inside it, as a button may not hold links or other buttons.

    The card becomes the section's (`claim`): its own header and collapse are switched off, so the
    section's header is the only one and the section's fold the only one. Set on the card, they hold
    through an ajax reload, which rebuilds the cards and so the stack; the reload redraws the
    section's header as well as its card, keeping the reader's fold. A card in a stack is not shown
    anywhere else on the page as well: its DOM ids would be there twice.

    The title, menu and folding are read from the card when the section is drawn, not when it is
    built, so a change made in ``cards_ready()`` reaches the header as it reaches the body.

    Args:
        card (CardBase): The card whose body is the section's.
        title (str, optional): The header's text, instead of the card's title. One of the two is
            needed, as the toggle is named by it. Escaped unless marked safe.
        menu (HtmlMenu or list, optional): Buttons beside the toggle instead of the card's own
            menu; a list is made a button group, as ``add_card(menu=[...])`` makes one.
        folded (bool, optional): Whether it starts folded, instead of whether the card is empty
            (``add_card(is_empty=True)``) or was built ``collapsed=True``.
    """

    def __init__(self, card, title=None, menu=None, folded=None):
        if not (hasattr(card, 'render') and hasattr(card, 'code')):
            raise TypeError(f'A section is a card, a dict of CardSection fields or a CardSection; got {card!r}')
        self.card = card
        self._title = title
        if isinstance(menu, (list, tuple)):
            menu = HtmlMenu(card.request, card.button_menu_type).add_items(*menu)
        self._menu = menu
        self._folded = folded

    @classmethod
    def build(cls, entry):
        """A section from a card, a dict of these fields, or a section; ``None`` for ``None``."""
        if entry is None or isinstance(entry, cls):
            return entry
        if isinstance(entry, dict):
            if 'card' not in entry:
                raise ValueError(f'A section dict needs its card: {entry!r}')
            return cls(**entry)
        return cls(card=entry)

    def claim(self):
        """Make the card the section's: its header and collapse off, and the section on it, so a
        reload of the card redraws the section's header too (``CardMixin.button_reload_card``)."""
        self.card.show_header = False
        self.card.enable_collapse = False
        self.card.section = self

    @property
    def title(self):
        # A title given here is escaped by the template's {{ }} unless marked safe; the card's own
        # was made text-unless-marked-safe when the card was built.
        return self._title if self._title is not None else getattr(self.card, 'title', None)

    @property
    def menu(self):
        return self._menu if self._menu is not None else getattr(self.card, 'menu', None)

    @property
    def folded(self):
        if self._folded is not None:
            return bool(self._folded)
        return bool(getattr(self.card, 'is_empty', False) or getattr(self.card, 'collapsed', None) is True)

    @property
    def id(self):
        # A hyphen, which a card's code (a slug of underscores, or a card_name) does not carry,
        # so a section's ids cannot be another card's.
        return f'{self.card.code}-section'

    @property
    def ids(self):
        """Every DOM id the section writes, checked against the view's card names."""
        return {self.id, f'{self.id}-header', f'{self.id}-body', f'{self.id}-toggle'}

    @property
    def has_menu(self):
        """Whether the menu will draw anything: its items counted as django-menus draws them."""
        menu = self.menu
        if not menu:
            return False
        if getattr(menu, 'menu_items', None) is None:
            return True
        return bool(visible_menu_items(menu))

    @property
    def has_controls(self):
        """Whether the card has header controls besides its menu (``_header_controls.html``)."""
        card = self.card
        return bool(getattr(card, 'ajax_reload', False) or getattr(card, 'searchable', False)
                    or getattr(card, 'exportable', False))

    @property
    def has_actions(self):
        return self.has_menu or self.has_controls

    def render_body(self):
        return self.card.render()

    def render_header(self, redraw=False):
        """The section's header, inside its ``-header`` element: what a reload redraws.

        Read from the card now, so the title is checked now: one set in ``cards_ready()`` counts,
        and one cleared there is caught. Whether the menu draws anything is worked out once here,
        as it asks every item's permissions. ``redraw`` is a reload's: the redrawn header then
        takes back the fold the reader left the section in.
        """
        if not self.title:
            raise ValueError(f'The section for card {self.card.code!r} has no title, and its toggle is '
                             f'named by one: give the card a title, or the section one')
        has_menu = self.has_menu
        return mark_safe(render_to_string('cards/standard/_section_header.html', {
            'section': self, 'card': self.card, 'request': self.card.request, 'redraw': redraw,
            'has_menu': has_menu, 'has_actions': has_menu or self.has_controls}))


def build_sections(entries, claim=True):
    """:class:`CardSection` objects for ``entries`` (cards, dicts or sections), skipping ``None``.

    A builder that decided it had nothing to add can hand back ``None`` in its place; it is left
    out, as a card group leaves one out. Every entry is checked before any card is claimed, so one
    bad entry leaves every card as it was. For a template of an application's own that wants the
    sections without a card around them: include ``cards/standard/_section_stack_body.html`` with
    ``sections=build_sections(cards)``.
    """
    sections = [section for section in (CardSection.build(entry) for entry in entries or ()) if section is not None]
    if claim:
        for section in sections:
            section.claim()
    return sections


SECTION_SCRIPT_MARK = '_django_cards_section_script_rendered'


def _stack_holds(card, target, _seen=None):
    """Whether ``card``'s own section stack holds ``target``, at any depth."""
    _seen = _seen if _seen is not None else set()
    if id(card) in _seen:
        return False
    _seen.add(id(card))
    info = getattr(card, 'extra_card_info', None) or {}
    for section in info.get('sections', ()):
        if section.card is target or _stack_holds(section.card, target, _seen):
            return True
    return False


class _SectionsHtml:
    """An add_sections() card's body, rendered the first time the card's template reads it.

    The card's html template prints ``extra_card_info.html``, and Django calls a callable it is
    handed there, so this is stored as the bound `render`: the sections' cards are drawn when the
    card is, after ``cards_ready()``, and once -- a second read returns the same markup.
    ``add_sections()`` makes a new one each call, so a later call's sections are in it. The
    toggle's script and the card stylesheet come once per request.
    """

    def __init__(self, card):
        self.card = card
        self.rendered = None
        self.rendering = False

    def render(self):
        if self.rendered is None:
            if self.rendering:
                # add_sections() refuses a stack inside itself; this is the backstop, for one made
                # some other way, rather than recursing until Python gives up.
                raise ValueError(f'The section stack of card {self.card.code!r} contains itself')
            self.rendering = True
            try:
                self.rendered = self._render()
            finally:
                self.rendering = False
        return self.rendered

    def _render(self):
        card = self.card
        sections = card.extra_card_info.get('sections', [])
        # Again now, against every card the view ended up with: one added after add_sections(),
        # later in setup_cards() or in cards_ready(), could take a section's id.
        taken = set(getattr(card.view, 'cards', None) or {})
        for section in sections:
            clash = section.ids & taken
            if clash:
                raise ValueError(f'Section ids {sorted(clash)} are card names on this view')
        holder = get_render_scope() or card.request
        script = holder is None or not getattr(holder, SECTION_SCRIPT_MARK, False)
        if script and holder is not None:
            setattr(holder, SECTION_SCRIPT_MARK, True)
        return mark_safe(render_to_string('cards/standard/_section_stack_body.html', {
            'sections': sections, 'request': card.request, 'section_script': script,
            'stack_id': f'{card.code}-sections'}))


@dataclass
class BannerTile:
    """One card in an :meth:`CardBase.add_banner_tiles` grid -- a large tile with a banner.

    For a list of courses, products or articles (a coloured banner, a title, a short
    description, a few stats, a progress bar and an action button), but nothing is fixed:
    every field but ``key`` is optional, and a tile draws only what it was given (the
    compact and detail layouts always draw their banner, in the default gradient if no banner
    field is set)::

        BannerTile(key='course_12', title='Getting Started',
                   description='This course covers the first steps, from setting up...',
                   banner_label='Projects', banner_icon='fas fa-folder-open',
                   step='Step 1 of 2', badge='Required for your role',
                   stats=[('fas fa-play-circle', '13 lessons'),
                          ('fas fa-question-circle', '8 quizzes')],
                   progress=0, status='Not started',
                   footer_label='Projects', footer_icon='fas fa-folder-open',
                   action_label='Start', action_url='/courses/12/')

    Args:
        key (str): Stable identifier; becomes the tile's DOM id, so it has to be unique on
            the page.
        title (str, optional): The tile's heading. Escaped.
        title_html (str, optional): The heading as markup, for one with a word in italics
            (``format_html('Learn <em>every</em> part of {}', product)``). Rendered unescaped;
            see the warning below. Used instead of ``title``, not alongside it.
        description (str, optional): A short paragraph under the title, cut to two lines by
            the stylesheet; the full text stays in the tile's ``title`` attribute. Escaped.
        banner_label (str, optional): Upper-case caption in the banner's bottom-left. Escaped.
        banner_icon (str, optional): Icon classes (``'fas fa-folder-open'``) drawn beside the
            caption and again, large and faded, on the banner's right.
        banner_background (str, optional): CSS ``background`` for the banner -- a colour or a
            gradient. Defaults to the stylesheet's blue gradient. It is written into a ``style``
            attribute, so it is checked (:func:`css_background`): anything that is not a colour
            or a gradient is dropped, and the banner keeps the default.
        image_url (str, optional): A banner image, drawn instead of the background and icon.
        step (str, optional): A flag in the banner's top-left (``'Step 1 of 2'``). Escaped.
        badge (str, optional): A pill under the description (``'Required for your role'``).
            Escaped.
        stats (list, optional): Short facts in a row under the badge. Each is a string or an
            ``(icon_classes, text)`` pair. Escaped.
        progress (int, optional): 0-100. A progress bar is drawn whenever this is not None,
            so 0 draws an empty bar -- pass None for no bar at all.
        status (str, optional): A quiet line under the progress bar (``'Not started'``).
            Escaped.
        footer_label (str, optional): Text in the footer's left (a category). Escaped.
        footer_icon (str, optional): Icon classes drawn before ``footer_label``.
        action_label (str, optional): The footer button's text. No button without one.
        action_url (str, optional): Where the button goes. A plain href, so a ``javascript:``
            URL that opens a modal works as well as a real one.
        action_css_class (str, optional): The button's classes. Left as None, they follow
            the layout at render time: ``'btn btn-sm btn-outline-primary'`` in the compact
            layout, ``'btn btn-primary'`` (full width) in the detail one, and each other
            layout's own button style.
        css_class (str, optional): Extra classes on the tile.
        layout (str, optional): ``'compact'`` (the default) is the grid tile: stats in a row,
            the button in the footer. ``'detail'`` is the single-item sidebar: stats one per
            line, a full-width button under them, then ``secondary_label`` and ``note``.
            ``'highlight'`` is a tile filled with ``banner_background`` (a purple gradient by
            default) in place of a banner: ``banner_icon``/``banner_label`` as a small
            upper-case line over the title and description, then ``status``, ``progress`` and
            a white button pinned to the bottom -- a learning path at the head of a grid.
            ``'feature'`` is a wide promotional slide: title, description and button on the
            left over a ``banner_background`` tint, and on the right decorative shapes with
            ``banner_icon`` in a white tile (no icon draws a single grey shape). Meant for a
            slider (``add_banner_tiles(slider=True)``); in a grid it takes the whole row.
            ``'plain'`` is text only, with no box: a large title and a quieter description (and
            an optional link), to introduce the tiles after it in a grid.
            ``'showcase'`` is a wide dark panel: title, description, ``points`` in two columns
            and a white button on the left; on the right a mosaic of a tall ``banner_icon``
            panel, a small diagram of ``flow`` names joined by lines, and a ``panel_icon``
            panel. Any panel not given is left out. In a grid it takes the whole row.
        banner_url (str, optional): Makes the banner a link, with a round play button over
            its middle -- a course preview.
        banner_caption (str, optional): Text under the play button (``'Preview this course'``).
            Without it or ``banner_label``, the banner link is named for screen readers by
            the title (``title_html``'s text, if that is how it is given), or ``'Preview'``.
            Escaped.
        callout_title, callout_text (str, optional): A tinted box under the banner (``'On your
            Estimator path'`` / ``'Step 1 of 2, required for your role.'``). Escaped.
        callout_icon (str, optional): Icon classes drawn at the callout's left.
        callout_link_label, callout_link_url (str, optional): A link at the end of the
            callout's text (``'See your path'``).
        secondary_label, secondary_url (str, optional): A quiet link under the button
            (``'Save for later'``).
        secondary_icon (str, optional): Icon classes drawn before ``secondary_label``.
        note (str, optional): A small centred line at the bottom (``'Your progress is saved as
            you go.'``). Escaped.
        points (list, optional): The showcase layout's list. Each is ``(icon_classes, text)``
            or ``(icon_classes, text, colour)``, the colour filling the icon's circle; without
            one the circles take turns through four soft colours. The text is escaped; the
            colour is written into a ``style`` attribute, so it is checked (:func:`css_background`),
            and one that is not a colour or a gradient takes its turn like a point given none.
        flow (list, optional): Names drawn as boxes joined by lines in a showcase panel
            (``['CRM', 'Projects', 'Gantt']``). Escaped.
        panel_icon (str, optional): Icon classes for the showcase's small icon panel.

    Warning:
        ``title_html`` is the one field rendered as-is, for the same reason as
        ``Tile.heading_html``: build it with :func:`~django.utils.html.format_html` and never
        pass a value from a form or a model field straight into it.

        The URL fields (``action_url``, ``banner_url``, ``callout_link_url``,
        ``secondary_url``, ``image_url``) are escaped, but escaping does not stop a
        ``javascript:`` URL, which they allow on purpose, as ``Tile.edit_url`` does. Build
        them in code, and never pass in a URL a user typed without checking its scheme.

    The detail layout, as a sidebar on a course's own page::

        BannerTile(key='course_12', title=None, layout='detail',
                   banner_icon='fas fa-folder-open', banner_url=course.preview_url,
                   banner_caption='Preview this course',
                   callout_icon='fas fa-route', callout_title='On your Estimator path',
                   callout_text='Step 1 of 2, required for your role.',
                   callout_link_label='See your path', callout_link_url=path_url,
                   stats=[('far fa-play-circle', '13 lessons in 2 sections'),
                          ('far fa-question-circle', '8 quizzes to check your understanding'),
                          ('fas fa-award', 'Certificate of completion')],
                   action_label='Start this course', action_url=course.start_url,
                   secondary_label='Save for later', secondary_icon='far fa-bookmark',
                   secondary_url=save_url, note='Your progress is saved as you go.')
    """

    LAYOUTS = ('compact', 'detail', 'highlight', 'feature', 'plain', 'showcase')
    # The showcase points' icon circles, in turn, when a point names no colour of its own.
    POINT_COLOURS = ('#e3cde6', '#fbe3a1', '#c9ecd8', '#dfe3ea')

    key: str
    title: str = None
    title_html: str = None
    description: str = None
    banner_label: str = None
    banner_icon: str = None
    banner_background: str = None
    image_url: str = None
    step: str = None
    badge: str = None
    stats: list = field(default_factory=list)
    progress: int = None
    status: str = None
    footer_label: str = None
    footer_icon: str = None
    action_label: str = None
    action_url: str = None
    action_css_class: str = None
    css_class: str = None
    layout: str = 'compact'
    banner_url: str = None
    banner_caption: str = None
    callout_title: str = None
    callout_text: str = None
    callout_icon: str = None
    callout_link_label: str = None
    callout_link_url: str = None
    secondary_label: str = None
    secondary_url: str = None
    secondary_icon: str = None
    note: str = None
    points: list = field(default_factory=list)
    flow: list = field(default_factory=list)
    panel_icon: str = None

    ACTION_CSS_CLASSES = {'detail': 'btn btn-primary',
                          'highlight': 'btn django-card__banner-tile-highlight-action',
                          'feature': 'btn django-card__banner-tile-feature-action',
                          'plain': 'django-card__banner-tile-plain-action',
                          'showcase': 'btn django-card__banner-tile-showcase-action',
                          }

    def __post_init__(self):
        if self.layout not in self.LAYOUTS:
            raise ValueError(f'BannerTile layout is one of {self.LAYOUTS}; got {self.layout!r}')
        # Check the list and number fields now, so bad input fails where the tile is built
        # rather than as a 500 when the page renders -- whichever layout the tile has. A bare
        # string is refused: iterated, it would draw a stat, point or box per character.
        for name in ('stats', 'points', 'flow'):
            value = getattr(self, name)
            if value is not None and not isinstance(value, (list, tuple)):
                raise TypeError(f'BannerTile {name} is a list; got {type(value).__name__} {value!r}')
        self.stat_items
        self.point_items
        self.progress_percent

    @property
    def action_classes(self):
        """`action_css_class`, or the layout's default -- worked out here, not in __post_init__,
        so a tile whose layout changes later (dataclasses.replace) gets that layout's button."""
        if self.action_css_class is not None:
            return self.action_css_class
        return self.ACTION_CSS_CLASSES.get(self.layout, 'btn btn-sm btn-outline-primary')

    @property
    def plain_title(self):
        """The title as plain text -- `title`, or `title_html` with its tags stripped -- for
        places markup cannot go, such as the banner link's aria-label."""
        if self.title:
            return self.title
        if self.title_html:
            return unescape(strip_tags(self.title_html)).strip() or None
        return None

    @property
    def heading(self):
        """The tile's title: `title_html` as-is (see the class's warning), else `title`, which
        the template escapes."""
        if self.title_html:
            return mark_safe(self.title_html)
        return self.title

    @property
    def is_detail(self):
        return self.layout == 'detail'

    @property
    def is_highlight(self):
        return self.layout == 'highlight'

    @property
    def is_feature(self):
        return self.layout == 'feature'

    @property
    def is_plain(self):
        return self.layout == 'plain'

    @property
    def is_showcase(self):
        return self.layout == 'showcase'

    @property
    def point_items(self):
        """`points` as {'icon', 'text', 'colour'} dicts, colours filled in turn where missing."""
        items = []
        for index, point in enumerate(self.points or ()):
            if not isinstance(point, (list, tuple)) or len(point) not in (2, 3):
                raise ValueError(f'A point is (icon_classes, text) or (icon_classes, text, colour); '
                                 f'got {point!r}')
            icon, text = point[0], point[1]
            # Written into `style="background: ..."`, so checked as a background (a gradient
            # fills a circle as well as a colour does); one that is not takes its turn from
            # POINT_COLOURS as a point with none does.
            colour = css_background(point[2]) if len(point) == 3 else None
            if colour is None:
                colour = self.POINT_COLOURS[index % len(self.POINT_COLOURS)]
            items.append({'icon': icon or '', 'text': text, 'colour': colour})
        return items

    @property
    def background_css(self):
        """`banner_background` as the templates write it into a ``style``: checked by
        :func:`css_background`, so one that is not a colour or a gradient is dropped and the
        banner keeps the stylesheet's own, as if none had been given."""
        return css_background(self.banner_background)

    @property
    def has_panels(self):
        return bool(self.banner_icon or self.flow or self.panel_icon)

    @property
    def has_title(self):
        return bool(self.title or self.title_html)

    @property
    def has_callout(self):
        return bool(self.callout_title or self.callout_text or self.callout_link_label)

    @classmethod
    def build(cls, tile):
        """Return `tile` as a BannerTile, accepting a dict of the same fields; see Tile.build."""
        if isinstance(tile, cls):
            return tile
        if isinstance(tile, dict):
            return cls(**tile)
        raise TypeError(f'add_banner_tiles() takes BannerTile objects or dicts of BannerTile '
                        f'fields, not {type(tile).__name__}')

    @property
    def stat_items(self):
        """`stats` as {'icon', 'text'} dicts, for the same reason as Tile.meta_lines."""
        items = []
        for stat in self.stats or ():
            if isinstance(stat, (list, tuple)):
                if len(stat) != 2:
                    raise ValueError(f'A stat pair is (icon_classes, text); got {stat!r}')
                icon, text = stat
            else:
                icon, text = None, stat
            items.append({'icon': icon or '', 'text': text})
        return items

    @property
    def progress_percent(self):
        """`progress` clamped to 0-100 and rounded, so a bad figure cannot push the bar out
        of its track and 99.6 is not drawn as 99."""
        if self.progress is None:
            return None
        try:
            progress = float(self.progress)
        except (TypeError, ValueError):
            raise ValueError(f'BannerTile progress is a number from 0 to 100 or None; '
                             f'got {self.progress!r}') from None
        if progress != progress:  # NaN
            raise ValueError('BannerTile progress is a number from 0 to 100 or None; got NaN')
        return round(max(0, min(100, progress)))  # clamp first: rounding an infinity raises

    @property
    def has_footer(self):
        """The compact layout's footer row; the others draw their button in the body."""
        if self.is_highlight or self.is_feature or self.is_plain or self.is_showcase:
            return False
        if self.is_detail:
            return bool(self.footer_label or self.footer_icon)
        return bool(self.footer_label or self.footer_icon or self.action_label)


class CardBase:
    """
    Card Framework for Django Views

    This module defines the `CardBase` class and associated constants used to render
    dynamic, configurable card-style UI components within Django views. Cards are modular
    HTML blocks that support various types of content presentation, such as:

    - Object detail fields (label/value pairs)
    - Data tables (including sortable and reorderable variants)
    - HTML fragments
    - Selectable lists
    - Grouped or nested card layouts

    Each card type supports advanced features such as:
    - Custom row styles and templates
    - Bootstrap-compatible layout options
    - Action button menus and tabbed interfaces
    - Auto-fetching of model field values with display formatting
    - Integration with django-datatables and django-menus

    Card rendering is customizable via Django templates and context injection,
    enabling easy reuse across views for admin dashboards, detail views, and inspectors.

    Common use cases include:
    - Object inspectors in a detail view
    - Nested layout containers in dashboards
    - Scrollable list selections with detail-on-click
    - Tabbed or collapsible card groups

    Main Classes:
        - `CardBase`: Core card logic for managing structure, rendering, and content population.

    Constants:
        - `CARD_TYPE_STANDARD`: Standard label/value detail card
        - `CARD_TYPE_DATATABLE`: Embedded datatable
        - `CARD_TYPE_ORDERED_DATATABLE`: Datatable with drag-and-drop ordering
        - `CARD_TYPE_HTML`: Arbitrary HTML card
        - `CARD_TYPE_LIST_SELECTION`: Scrollable list of items (click to trigger detail)
        - `CARD_TYPE_CARD_GROUP`: Group of cards rendered together
        - `CARD_TYPE_CARD_LAYOUT`: Nested layout container for arranging child card groups

    Intended to be used in combination with views that inherit from `CardList`, `CardTree`, or
    custom mixins providing card construction logic.

    """
    templates = {'default': {'name': 'cards/standard/default.html',
                             'context': {'card_css_class': 'card django-card',
                                         'card_body_css_class': 'card-body cards-list',
                                         'item_css_class': 'list-group-item'}},
                 'default_body': {'name': 'cards/standard/default_body.html',
                                  'context': {'card_body_css_class': 'card-body cards-list',
                                              'item_css_class': 'list-group-item'}},
                 'table': {'name': 'cards/standard/table.html',
                           'context': {'card_css_class': 'card django-card',
                                       'card_body_css_class': 'card-body cards-list',
                                       'table_css_class': 'table'}},
                 'table_body': {'name': 'cards/standard/table_body.html'},
                 'datatable': {'name': 'cards/standard/datatable.html',
                               'context': {'card_css_class': 'card django-card',
                                           'card_body_css_class': 'card-body cards-list'}},
                 'html': {'name': 'cards/standard/html.html',
                          'context': {'card_css_class': 'card django-card',
                                      'card_body_css_class': 'card-body cards-list'}},
                 'card_group': {'name': 'cards/standard/card_group.html',
                                'context': {'card_css_class': 'card django-card',
                                            'card_body_css_outer_class': 'card-body',
                                            'card_body_css_inner_class': 'row cards-list'}},
                 'card_layout': {'name': 'cards/standard/card_group.html',
                                 'context': {'card_body_css_outer_class': '',
                                             'card_css_class': '',
                                             'card_body_css_inner_class': 'row'}},
                 'list_selection': {'name': 'cards/standard/list_selection.html',
                                    'context': {'card_css_class': 'card django-card',
                                                'card_link_css_class': 'list-group-item cards-list-group-item',
                                                'card_body_css_class': 'overflow-auto',
                                                'card_body_css_style': 'height: calc(100vh - 150px);',
                                                'enable_reorder': False,
                                                'modal': False}},
                 'list_selection_reorder': {'name': 'cards/standard/list_selection.html',
                                          'context': {'card_css_class': 'card django-card',
                                                      'card_link_css_class': 'list-group-item cards-list-group-item',
                                                      'card_body_css_class': 'overflow-auto',
                                                      'card_body_css_style': 'height: calc(100vh - 150px);',
                                                      'enable_reorder': True,
                                                      'modal': False}},
                 'tree_selection': {'name': 'cards/standard/tree_selection.html',
                                    'context': {'card_css_class': 'card django-card',
                                                'card_body_css_class': 'card-body cards-list overflow-auto',
                                                'card_body_css_style': 'height: calc(100vh - 150px);',
                                                'tree_themes': json.dumps({'name': 'proton', 'responsive': True}),
                                                'tree_plugins': json.dumps(['wholerow'])}},
                 'blank': {'name': 'cards/standard/blank.html'},
                 'image_gallery': {'name': 'cards/standard/image_gallery.html',
                                   'context': {'card_css_class': 'card django-card',
                                               'card_body_css_class': 'card-body cards-list'}},
                 'tiles': {'name': 'cards/standard/tiles.html',
                           'context': {'card_css_class': 'card django-card',
                                       'card_body_css_class': 'card-body cards-list'}},
                 # add_sections(): the pack's own html card, its body the stack (`_sections_html`),
                 # so the stack needs no card template of its own in either pack.
                 'section_stack': {'name': 'cards/standard/html.html',
                                   'context': {'card_css_class': 'card django-card',
                                               'card_body_css_class': 'card-body p-0'}},
                 'banner_tiles': {'name': 'cards/standard/banner_tiles.html',
                                  'context': {'card_css_class': 'card django-card',
                                              'card_body_css_class': 'card-body cards-list'}},
                 'message': {'name': 'cards/standard/message.html',
                             'context': {'card_css_class': 'card django-card',
                                         'alert_css_class': 'alert-warning'}},
                 'linked_datatables': {'name': 'cards/standard/linked_datatables.html',
                                       'context': {'card_css_class': 'card django-card',
                                                   'card_body_css_class': 'card-body'}},
                 'accordion': {'name': 'cards/standard/accordion.html',
                               'context': {'card_css_class': 'card django-card',
                                           'card_body_css_class': 'card-body'}},
                 'panel_layout_card': {'name': 'cards/standard/html.html',
                                       'context': {'card_css_class': '',
                                                   'card_body_css_class': ''}},
                 'iframe': {'name': 'cards/standard/iframe.html',
                            'context': {'card_css_class': 'card django-card',
                                        'card_body_css_class': 'card-body p-0'}},
                 'treegrid': {'name': 'cards/standard/treegrid.html',
                              'context': {'card_css_class': 'card django-card',
                                          'card_body_css_class': 'card-body cards-list'}}}

    ajax_commands = ['datatable']

    template_defaults = {CARD_TYPE_STANDARD: 'default',
                         CARD_TYPE_DATATABLE: 'datatable',
                         CARD_TYPE_ORDERED_DATATABLE: 'datatable',
                         CARD_TYPE_HTML: 'html',
                         CARD_TYPE_LIST_SELECTION: 'list_selection',
                         CARD_TYPE_CARD_GROUP: 'card_group',
                         CARD_TYPE_CARD_LAYOUT: 'card_layout',
                         CARD_TYPE_CARD_MESSAGE: 'message',
                         CARD_TYPE_LINKED_DATATABLES: 'linked_datatables',
                         CARD_TYPE_ACCORDION: 'accordion',
                         CARD_TYPE_PANEL_LAYOUT: 'panel_layout_card',
                         CARD_TYPE_IFRAME: 'iframe',
                         CARD_TYPE_TREEGRID: 'treegrid'}

    button_menu_type = 'button_group'
    tab_menu_type = 'tabs'
    default_empty_template = 'message'

    def __init__(self, request, code=None, view=None, details_object=None, title=None,
                 menu=None, tab_menu=None, sub_tab_menu=None, template_name=None, call_details_data=False,
                 group_type=CARD_TYPE_STANDARD, show_created_modified_dates=False,
                 footer=None, extra_card_context=None,
                 is_empty=False, empty_template_name=None, empty_message='N/A',
                 collapsed=None, hidden_if_blank_or_none=None, hidden_if_zero=None,
                 show_header=True, header_icon=None, header_css_class='',
                 ajax_reload=False, reload_interval=None,
                 searchable=False, exportable=False,
                 column_search=False,
                 border=None,
                 **kwargs):
        """
        Initializes a card instance used to render a block of content within a view.

        Cards are modular UI components that can display object details, tables, lists, HTML,
        or even act as layout containers for grouping and positioning other cards.

        Args:
            request (HttpRequest): The current request object, used for context resolution.
            code (str, optional): A unique identifier for the card (used as a lookup key).
            view (View, optional): The parent view instance that is generating the card.
            details_object (object, optional): The main data object to be displayed in the card.
            title (str, optional): The heading/title displayed on the card.
            menu (list, optional): Optional list of action menu items for the card.
            tab_menu (list, optional): Optional tab menu items for the card.
            sub_tab_menu (list, optional): A second, quieter row of tabs under ``tab_menu`` -- the
                pages under the top tab in view. Items or an HtmlMenu. Not drawn when it shows one
                tab or none as it renders, since one repeats the tab it sits under. Needs
                ``tab_menu``: without one this raises ``ValueError``.
            template_name (str, optional): Template to be used for rendering the card.
            call_details_data (bool, optional): Whether to invoke a method to populate dynamic data. Defaults to False.
            group_type (int, optional): Defines the visual and functional type of the card. Defaults to CARD_TYPE_STANDARD.
                Valid values include:
                    - CARD_TYPE_STANDARD (1): Default detail-style card
                    - CARD_TYPE_DATATABLE (2): A card containing a data table
                    - CARD_TYPE_ORDERED_DATATABLE (3): A card with a sortable/ordered table
                    - CARD_TYPE_HTML (4): A card with raw or rendered HTML content
                    - CARD_TYPE_LIST_SELECTION (5): A card showing a selectable list of entries
                    - CARD_TYPE_CARD_GROUP (6): A logical grouping of cards (e.g. tabbed or side-by-side)
                    - CARD_TYPE_CARD_LAYOUT (7): A container card that can hold child card groups
            show_created_modified_dates (bool, optional): If True, adds created/modified timestamps to the card. Defaults to False.
            footer (str, optional): Optional footer content to display at the bottom of the card.
            extra_card_context (dict, optional): Extra context passed to the card template.
            is_empty (bool, optional): Whether the card should be considered empty (e.g. for fallback rendering). Defaults to False.
            empty_template_name (str, optional): Template to use if the card is empty.
            empty_message (str, optional): Message to display when the card has no data. Defaults to 'N/A'.
            collapsed (bool, optional): If True, the card is initially collapsed.
            hidden_if_blank_or_none (list, optional): Field names to hide if their values are blank or None.
            hidden_if_zero (list, optional): Field names to hide if their values are zero.
            show_header (bool, optional): Whether to show the header / title of the card.
            border (str/bool, optional): Card chrome. ``None`` (or ``True``) keeps the
                default Bootstrap card border. ``'thin'`` draws a 1px hairline around the
                card. ``'none'`` (or ``False``) removes the border so the card can be
                just content — for
                example a row of icons with no box.
            **kwargs: Additional keyword arguments for custom behavior or extension.

        Notes:
            - Layout cards (CARD_TYPE_CARD_LAYOUT) support nesting of other cards via `add_child_card_group()`.
        """

        if code is None:
            if title is not None:
                code = slugify(title).replace('-', '_') + '_card'
            else:
                code = random_string()

        self.code = code
        self.view = view
        self.details_object = details_object
        self.request = request

        self.show_created_modified_dates = show_created_modified_dates
        self.footer = footer

        self.rows = []
        self._row_styles = {}
        self._default_row_styles = None
        # Text unless it says otherwise, as a row's value and label are (`escape_value`): a title
        # that is markup -- `format_html`, `mark_safe`, a rendered template or menu -- is marked
        # safe where it is made. The code above is slugified from the title as it was passed, so
        # escaping here does not turn 'R&D Details' into `ramp_d_details_card`.
        if title is not None:
            self.title = escape_value(title)
        else:
            self.title = None
        self.created_modified_dates = self.get_created_modified_dates(details_object=details_object)
        if isinstance(menu, (list, tuple)):
            menu = HtmlMenu(self.request, self.button_menu_type).add_items(*menu)
        self.menu = menu
        if isinstance(tab_menu, (list, tuple)):
            tab_menu = HtmlMenu(self.request, self.tab_menu_type).add_items(*tab_menu)
        if tab_menu is not None and kwargs.pop('scrollable_tab_menu', False):
            tab_menu = ScrollableTabMenu(tab_menu)
        self.tab_menu = tab_menu
        self.call_details_data = call_details_data
        self.enable_collapse = collapsed is not None
        self.collapsed = collapsed
        self.hidden_if_blank_or_none = hidden_if_blank_or_none
        self.hidden_if_zero = hidden_if_zero
        self.show_header = show_header
        # Kept so a template or a caller can ask afterwards -- e.g. to start an empty card folded.
        # The flag also picks the empty template below, after which there is no other way to tell.
        self.is_empty = is_empty
        self.header_icon = header_icon
        self.header_css_class = header_css_class
        self.ajax_reload = ajax_reload
        self.reload_interval = reload_interval
        self.searchable = searchable
        self.exportable = exportable
        self.column_search = column_search
        self.border = normalize_card_border(border)
        # Set by the body-building methods whose markup needs cards.css -- add_tiles so far.
        # `border` asks for the stylesheet too, and is kept separate because it is a caller's
        # option rather than something a method turns on.
        self.requires_card_css = False

        if isinstance(sub_tab_menu, (list, tuple)):
            sub_tab_menu = HtmlMenu(self.request, self.tab_menu_type).add_items(*sub_tab_menu)
        if sub_tab_menu is not None:
            if self.tab_menu is None:
                raise ValueError('sub_tab_menu is a row under tab_menu, and this card has no tab_menu')
            # Wrapped whatever it holds now: whether the row is drawn is decided as it renders.
            self.tab_menu = TabMenuWithSubRow(self.tab_menu, sub_tab_menu)
            self.requires_card_css = True  # the sub row's styling lives in cards.css

        if is_empty:
            self.group_type = CARD_TYPE_STANDARD
            self.extra_card_context = {'message': empty_message}
            if empty_template_name is None:
                self.template_name = self.default_empty_template
            else:
                self.template_name = empty_template_name
        else:
            self.extra_card_context = extra_card_context
            self.template_name = template_name
            self.group_type = group_type
        self.extra_card_info = {}
        self.add_extra_card_info(extra_info=self.extra_card_info, group_type=self.group_type, **kwargs)

        self.process_data()
        self.child_card_groups = []

    # noinspection PyMethodMayBeStatic
    def add_extra_card_info(self, extra_info, group_type, **kwargs):
        """
        Adds additional context or configuration to a card's extra info dictionary based on its group type.

        This method enriches the `extra_info` dictionary with data relevant to specific card types such as
        data tables or HTML blocks.

        Args:
            extra_info (dict): The dictionary to which extra card information will be added.
            group_type (int): The card type, used to determine what extra information is added.
                Supported values:
                    - CARD_TYPE_DATATABLE
                    - CARD_TYPE_ORDERED_DATATABLE
                    - CARD_TYPE_HTML
            **kwargs: Additional keyword arguments that provide data relevant to the given group type.
                - For data table cards:
                    - datatable_id (str): ID for the datatable (defaults to the card's code).
                    - datatable (object): The datatable instance or configuration.
                    - datatable_model (Model): The model backing the datatable, if any.
                    - setup_table (callable): A callable used to set up the datatable.
                    - order_field (str): Ordering field name for ordered datatables (defaults to 'order').
                - For HTML cards:
                    - html (str): The raw HTML content to render.

        Side Effects:
            - Mutates `extra_info` in-place by adding the appropriate keys for the given card type.
        """
        if group_type in (CARD_TYPE_DATATABLE, CARD_TYPE_ORDERED_DATATABLE):
            extra_info['datatable_id'] = kwargs.get('datatable_id', self.code)
            extra_info['datatable'] = kwargs.get('datatable')
            extra_info['datatable_model'] = kwargs.get('datatable_model')
            extra_info['setup_table'] = kwargs.get('setup_table')
            if group_type == CARD_TYPE_ORDERED_DATATABLE:
                extra_info['order_field'] = kwargs.get('order_field', 'order')
        elif group_type == CARD_TYPE_LINKED_DATATABLES:
            extra_info['datatables'] = kwargs.get('datatables', [])
        elif group_type == CARD_TYPE_ACCORDION:
            extra_info['panels'] = kwargs.get('panels', [])
            extra_info['multi_open'] = kwargs.get('multi_open', False)
            extra_info['full_height'] = kwargs.get('full_height', False)
            extra_info['min_height'] = kwargs.get('min_height', '300px')
        elif group_type in (CARD_TYPE_HTML, CARD_TYPE_PANEL_LAYOUT):
            extra_info['html'] = kwargs.get('html')
        elif group_type == CARD_TYPE_IFRAME:
            extra_info['iframe_url'] = kwargs.get('iframe_url', '')
            extra_info['iframe_srcdoc'] = kwargs.get('iframe_srcdoc', '')
            extra_info['iframe_height'] = kwargs.get('iframe_height', '400px')
            extra_info['iframe_sandbox'] = kwargs.get('iframe_sandbox', 'allow-scripts allow-same-origin')
            extra_info['iframe_id'] = kwargs.get('iframe_id', '')
            extra_info['iframe_name'] = kwargs.get('iframe_name', '')
        elif group_type == CARD_TYPE_TREEGRID:
            extra_info['treegrid_data_url'] = kwargs.get('treegrid_data_url', '')
            extra_info['treegrid_data_mode'] = kwargs.get('treegrid_data_mode', 'ajax')
            extra_info['treegrid_static_data'] = kwargs.get('treegrid_static_data', [])
            extra_info['treegrid_columns'] = kwargs.get('treegrid_columns', [])
            extra_info['treegrid_read_only'] = kwargs.get('treegrid_read_only', True)
            extra_info['treegrid_height'] = kwargs.get('treegrid_height', '600px')
            extra_info['treegrid_indentation'] = kwargs.get('treegrid_indentation', 20)
            extra_info['treegrid_icon_map'] = kwargs.get('treegrid_icon_map', {})
            extra_info['treegrid_show_filter'] = kwargs.get('treegrid_show_filter', True)
            # treegrid_show_filter switches the search box and the Expand/Collapse All pair
            # together, as it always has. treegrid_show_search and
            # treegrid_show_expand_buttons split that switch for a card that wants one
            # without the other; left as None they follow treegrid_show_filter.
            show_search = kwargs.get('treegrid_show_search')
            if show_search is None:
                show_search = extra_info['treegrid_show_filter']
            extra_info['treegrid_show_search'] = show_search
            show_expand_buttons = kwargs.get('treegrid_show_expand_buttons')
            if show_expand_buttons is None:
                show_expand_buttons = extra_info['treegrid_show_filter']
            extra_info['treegrid_show_expand_buttons'] = show_expand_buttons
            extra_info['treegrid_auto_hide_expand_buttons'] = kwargs.get(
                'treegrid_auto_hide_expand_buttons', False)
            extra_info['treegrid_expand_all'] = kwargs.get('treegrid_expand_all', False)
            # Passed by add_treegrid_card since 1.4.x but never stored, so the template's
            # lookup silently resolved to '' and the filter never auto-expanded whatever the
            # caller asked for. Stored now, and defaulted off to match what grids have
            # actually been doing since then -- a caller who wants it says so.
            extra_info['treegrid_filter_auto_expand'] = kwargs.get('treegrid_filter_auto_expand', False)
            extra_info['treegrid_show_column_filters'] = kwargs.get('treegrid_show_column_filters', False)
            extra_info['treegrid_toolbar'] = kwargs.get('treegrid_toolbar', [])
            extra_info['treegrid_toolbar_after'] = kwargs.get('treegrid_toolbar_after', [])
            extra_info['treegrid_toolbar_end'] = kwargs.get('treegrid_toolbar_end', [])
            extra_info['treegrid_submit_label'] = kwargs.get('treegrid_submit_label', 'Submit Selected')
            extra_info['treegrid_header_rows'] = kwargs.get('treegrid_header_rows', [])
            extra_info['treegrid_node_column'] = kwargs.get('treegrid_node_column', 0)
            extra_info['treegrid_save_mode'] = kwargs.get('treegrid_save_mode', 'auto')
            extra_info['treegrid_checkbox'] = kwargs.get('treegrid_checkbox', False)
            extra_info['treegrid_checkbox_column'] = kwargs.get('treegrid_checkbox_column', 0)
            # The three things a checkbox grid renders alongside the ticks. All on, as they
            # always were; each can be left out by a card whose rows carry their own actions.
            extra_info['treegrid_show_select_buttons'] = kwargs.get('treegrid_show_select_buttons', True)
            extra_info['treegrid_show_submit_button'] = kwargs.get('treegrid_show_submit_button', True)
            extra_info['treegrid_show_select_count'] = kwargs.get('treegrid_show_select_count', True)
            extra_info['treegrid_context_menu'] = kwargs.get('treegrid_context_menu', [])
            extra_info['treegrid_context_menu_json'] = json_for_script(
                [i for i in extra_info['treegrid_context_menu'] if isinstance(i, dict)])
            extra_info['treegrid_context_menu_html'] = kwargs.get('treegrid_context_menu_html', '')
            extra_info['treegrid_resizable'] = kwargs.get('treegrid_resizable', False)
            extra_info['treegrid_pagination'] = kwargs.get('treegrid_pagination', False)
            extra_info['treegrid_page_size'] = kwargs.get('treegrid_page_size', 50)
            extra_info['treegrid_js_filters'] = kwargs.get('treegrid_js_filters', [])
            extra_info['treegrid_current_node'] = kwargs.get('treegrid_current_node', '')

            sortable = kwargs.get('treegrid_sortable', False)
            drag_drop = kwargs.get('treegrid_drag_drop', False)
            if sortable and drag_drop:
                raise Exception('treegrid_sortable and treegrid_drag_drop cannot be enabled at the same time')
            extra_info['treegrid_sortable'] = sortable
            extra_info['treegrid_drag_drop'] = drag_drop

            extra_info['treegrid_form_field'] = kwargs.get('treegrid_form_field', '')
            extra_info['treegrid_row_click'] = kwargs.get('treegrid_row_click', '')
            extra_info['treegrid_default_selected'] = kwargs.get('treegrid_default_selected', [])
            extra_info['treegrid_drag_cross_level'] = kwargs.get('treegrid_drag_cross_level', False)
            extra_info['treegrid_nowrap'] = kwargs.get('treegrid_nowrap', False)
            # Pre-serialise for template JS
            extra_info['treegrid_icon_map_json'] = json_for_script(extra_info['treegrid_icon_map'])
            extra_info['treegrid_columns_json'] = json_for_script(extra_info['treegrid_columns'])
            extra_info['treegrid_toolbar_json'] = json_for_script(extra_info['treegrid_toolbar'])
            extra_info['treegrid_static_data_json'] = json_for_script(extra_info['treegrid_static_data'])
            extra_info['treegrid_js_filters_json'] = json_for_script(extra_info['treegrid_js_filters'])
            extra_info['treegrid_default_selected_json'] = json_for_script(extra_info['treegrid_default_selected'] or [])
            extra_info['treegrid_borderless'] = kwargs.get('treegrid_borderless', False)
            extra_info['treegrid_min_width'] = kwargs.get('treegrid_min_width', '600px')

    def add_boolean_entry(self, value, label=None, hidden=False, html_override=None,
                          entry_css_class=None, css_class=None,
                          menu=None, default_if=None, value_type=None, row_style=None, **kwargs):
        """
        Adds a boolean-style entry to the card, rendered as a green checkmark or red cross icon.

        This method is typically not called directly. It is invoked internally by `add_entry` either:
          - when `value_type='boolean'` is explicitly set, or
          - when the value is detected to be a boolean via `isinstance(value, bool)`.

        Args:
            value (bool): The boolean value to display. Renders a green check icon if True, red cross if False.
            label (str, optional): The label to display alongside the icon.
            hidden (bool, optional): If True, the entry is not shown.
            html_override (str or HtmlElement, optional): Custom HTML override for full value rendering.
            entry_css_class (str, optional): CSS class for the value/content area.
            css_class (str, optional): CSS class for the row container.
            menu (list, optional): Optional action menu items for the entry.
            default_if (callable, optional): Optional function to determine if default text should be used.
            value_type (str, optional): Rendering hint (usually 'boolean') passed from higher-level `add_entry`.
            row_style (str, optional): Named row style for custom layout, if defined.
            **kwargs: Additional keyword arguments for rendering or substitution in styled rows.

        Returns:
            dict: A dictionary representing the entry, suitable for appending to a card row.

        Example:
            # Usually called indirectly via add_entry:
            card.add_entry(label='Is Active?', value=True)
            card.add_entry(label='Confirmed', value=False, value_type='boolean')
            """
        if value:
            entry = self._add_entry_internal(value=mark_safe('<i class="fas fa-check" style="color:green;"></i>'),
                                             label=label,
                                             hidden=hidden,
                                             html_override=html_override,
                                             entry_css_class=entry_css_class,
                                             css_class=css_class,
                                             menu=menu,
                                             default_if=default_if,
                                             value_type=value_type,
                                             row_style=row_style,
                                             **kwargs)
        else:
            entry = self._add_entry_internal(value=mark_safe('<i class="fas fa-times" style="color:red;"></i>'),
                                             label=label,
                                             hidden=hidden,
                                             html_override=html_override,
                                             entry_css_class=entry_css_class,
                                             css_class=css_class,
                                             menu=menu,
                                             default_if=default_if,
                                             value_type=value_type,
                                             row_style=row_style,
                                             **kwargs)
        return entry

    def add_date_entry(self, value, label=None, hidden=False, html_override=None,
                       entry_css_class=None, css_class=None, menu=None, default_if=None,
                       value_type=None, row_style=None, **kwargs):
        """
        Adds a date-style entry to the card, formatted as 'dd/mm/yy'.

        This method is normally called internally by `add_entry`, either:
          - when `value_type='date'` is explicitly provided, or
          - when the value is identified as a `datetime.date` instance via `isinstance`.

        Args:
            value (datetime.date or datetime.datetime): The date to display.
            label (str, optional): Label to display alongside the date.
            hidden (bool, optional): If True, the entry is not shown.
            html_override (str or HtmlElement, optional): Custom HTML to override the value display.
            entry_css_class (str, optional): CSS class for the value/content span or div.
            css_class (str, optional): CSS class for the row container.
            menu (list, optional): Optional list of menu items or actions for this entry.
            default_if (callable, optional): Function to determine if the default should be shown.
            value_type (str, optional): Rendering hint (e.g., 'date') passed from `add_entry`.
            row_style (str, optional): Optional row style to apply to this entry.
            **kwargs: Additional arguments for layout, styling, or context substitution.

        Returns:
            dict: The generated entry dictionary, suitable for inclusion in a card row.

        Example:
            # Typically called via add_entry:
            card.add_entry(label='Created On', value=obj.created)
            card.add_entry(label='Expires', value=date(2024, 12, 31), value_type='date')
        """
        new_value = value.strftime('%d/%m/%y')
        return self._add_entry_internal(value=new_value,
                                        label=label,
                                        hidden=hidden,
                                        html_override=html_override,
                                        entry_css_class=entry_css_class,
                                        css_class=css_class,
                                        menu=menu,
                                        default_if=default_if,
                                        value_type=value_type,
                                        row_style=row_style,
                                        **kwargs)

    def add_row(self, *args, extra_row_kwargs=None):
        """
        Adds a row to the card, containing one or more field entries.

        Each argument can be:
          - A string: treated as a field name (auto-fetched from `details_object`).
          - A dict: passed as keyword arguments to `_add_entry_internal()`.

        The method supports both single-entry and multi-entry rows:
          - If only one entry is provided, a standard row is added.
          - If multiple entries are provided, the row is styled using Bootstrap column classes
            (`col-sm-6`, `col-sm-4`, etc.) unless explicitly overridden via `entry_css_class`.

        Args:
            *args: Field names or entry definition dictionaries.
            extra_row_kwargs (dict, optional): Additional keyword arguments applied to each entry.

        Side Effects:
            - Appends a structured row dictionary to `self.rows`.

        Example:
            card.add_row('first_name', 'last_name')

            card.add_row(
                {'field': 'email', 'label': 'Email Address'},
                {'field': 'phone', 'label': 'Phone Number'},
                extra_row_kwargs={'css_class': 'text-muted'}
            )
        """
        if extra_row_kwargs is None:
            extra_row_kwargs = {}
        entries = []
        for arg in args:
            if isinstance(arg, str):
                entry = self._add_entry_internal(field=arg, **extra_row_kwargs)
            else:
                entry = self._add_entry_internal(**arg, **extra_row_kwargs)
            if entry is not None:
                entries.append(entry)

        if (entry_len := len(entries)) > 0:
            if entry_len == 1:
                row = {'type': 'standard', 'entries': entries}
            else:
                css_types = {2: 'col-sm-6', 3: 'col-sm-4', 4: 'col-sm-3'}
                entry_css_class = css_types.get(entry_len, 'col-sm-6')

                for entry in entries:
                    if entry.get('entry_css_class') is None:
                        entry['entry_css_class'] = entry_css_class

                row = {'type': 'multiple', 'entries': entries}
            self.rows.append(row)

    def add_entry(self, value=None, field=None, label=None, entry_css_class=None, css_class=None,
                  default='N/A', link=None, hidden=False, hidden_if_blank_or_none=None, hidden_if_zero=None,
                  html_override=None, value_method=None, value_type=None, default_if=None, row_style=None,
                  tooltip=None, value_link=None, css_class_method=None,
                  badge=None, icon=None, copy_to_clipboard=False, truncate=None,
                  prefix=None, suffix=None, placeholder=None, status_dot=None,
                  progress_bar=None, image=None, timestamp=False,
                  help_text=None, boolean_icon=False, popover=None, separator=False,
                  number_format=None, rating=None,
                  show_if=None, auto_link=False, sparkline=False, old_value=None,
                  **kwargs):
        """
        Adds a single entry (label/value pair) to the card as a new row.

        Entries can be simple strings, resolved fields from an object, or complex structures using a named
        `row_style` with HTML elements for fine-grained layout.

        A value and a label are text: they are escaped when the row is drawn, whether they were
        passed in or read off `details_object`, unless they are marked safe (``mark_safe``,
        ``format_html``, a rendered template). Markup meant to show as markup has to be marked
        safe where it is made. `html_override`, a row style and `merge_string` are markup, and
        the value put into them is escaped the same way.

        Args:
            value (any, optional): The value to display. Can be a string, number, dict (for `row_style`), or None.
                Escaped unless it is marked safe, and so is a value read from `field`.
            field (str, optional): Field name to auto-fetch value from `details_object` if `value` is not provided.
            label (str, optional): Label to display alongside the value. Escaped unless it is marked safe.
            entry_css_class (str, optional): CSS class for the value span/div.
            css_class (str, optional): CSS class for the value heading (standard template).
            row_css_class (str, optional): CSS class for the row itself. In the table template
                this lands on the ``<tr>``, so a line can be highlighted with e.g.
                ``row_css_class='table-warning'``.
            default (str, optional): Default text to display if the value is None or empty. Defaults to 'N/A'.
            link (str or callable, optional): URL or link generator for making the value a hyperlink.
            hidden (bool, optional): If True, the entry is not shown.
            hidden_if_blank_or_none (bool, optional): If True, hides the entry if the value is blank or None.
            hidden_if_zero (bool, optional): If True, hides the entry if the value is 0.
            html_override (str, optional): Markup drawn in place of the value, with `%1%` standing for the
                value. The markup is used as it is; the value put into it is escaped unless it is marked safe.
            value_method (str or callable, optional): A method or method name to compute the value dynamically.
            value_type (str, optional): Optional rendering hint (e.g., 'currency', 'boolean', etc.).
            default_if (callable, optional): A function to conditionally apply the default.
            row_style (str, optional): A named layout style (defined via `add_row_style`) that replaces default rendering.
            **kwargs: Additional named parameters used for row style substitution or link construction.

        Side Effects:
            - Appends a new row containing this entry to `self.rows`.

        Example:
            card = self.add_card(title='Row Style Examples no DB')

            card.add_row_style('test', html=HtmlDiv([
                HtmlElement('span', contents=[HtmlElement('h4', contents='{label}')]),
                HtmlElement('span', contents='{value}')
            ]))

            card.add_entry(value='Row Style line', label='Styled Entry', row_style='test')

            card.add_entry(
                value={'v1': 'foo', 'v2': 'bar'},
                label='Multi-value',
                row_style='multi_value'
            )
        """

        entry = self._add_entry_internal(value=value,
                                         field=field,
                                         label=label,
                                         entry_css_class=entry_css_class,
                                         css_class=css_class,
                                         default=default,
                                         link=link,
                                         hidden=hidden,
                                         hidden_if_blank_or_none=hidden_if_blank_or_none,
                                         hidden_if_zero=hidden_if_zero,
                                         html_override=html_override,
                                         value_method=value_method,
                                         value_type=value_type,
                                         default_if=default_if,
                                         row_style=row_style,
                                         tooltip=tooltip,
                                         value_link=value_link,
                                         css_class_method=css_class_method,
                                         badge=badge,
                                         icon=icon,
                                         copy_to_clipboard=copy_to_clipboard,
                                         truncate=truncate,
                                         prefix=prefix,
                                         suffix=suffix,
                                         placeholder=placeholder,
                                         status_dot=status_dot,
                                         progress_bar=progress_bar,
                                         image=image,
                                         timestamp=timestamp,
                                         help_text=help_text,
                                         boolean_icon=boolean_icon,
                                         popover=popover,
                                         separator=separator,
                                         number_format=number_format,
                                         rating=rating,
                                         show_if=show_if,
                                         auto_link=auto_link,
                                         sparkline=sparkline,
                                         old_value=old_value,
                                         **kwargs)
        if entry is not None:
            self.rows.append({'type': 'standard', 'entries': [entry]})

    def add_html_entry(self, template_name, context=None, **kwargs):
        """
        Renders a template to HTML and adds it as a custom HTML row in the card.

        This method allows full control over the row layout using a Django template. Context variables
        from both `context` and `**kwargs` are merged and passed to the template.

        Args:
            template_name (str): The path to the Django template to render.
            context (dict, optional): Context dictionary to pass to the template.
            **kwargs: Additional context variables, and optional extra keys included in the final row dict.

        Side Effects:
            - Appends a row to `self.rows` with type `'html'` and rendered HTML content.

        Example:
            card.add_html_entry(
                template_name='cards/custom_row.html',
                context={'title': 'Custom Content'},
                css_class='my-custom-row'
            )
        """
        if context is None:
            context = {}
        context = {**context, **kwargs}
        html = render_to_string(template_name=template_name, context=context)
        self.rows.append({'type': 'html', 'html': html, **kwargs})

    def add_html_string_entry(self, html, exclude_td=True, **kwargs):
        if isinstance(html, str):
            rendered = html
        elif callable(getattr(html, "render", None)):
            rendered = html.render()
        else:
            rendered = "html must be a string or an object with a callable 'render' method"

        self.rows.append({'type': 'html', 'html': rendered, 'exclude_td': exclude_td, **kwargs})

    def add_row_style(self, name, html, is_default=False):
        """
        Defines a named row style for custom rendering of card entries.

        A row style allows you to fully control the HTML layout of an entry by using placeholders such as
        `{label}`, `{value}`, or custom keys (e.g., `{test}`, `{value[v1]}`) that can be substituted at render time.

        The style is markup and is used as it is, so it must not have data written into it: put the data in a
        placeholder instead. What fills a placeholder is escaped unless it is marked safe, and so is anything
        looked up on it (`{value[v1]}`).

        Args:
            name (str): The name of the style, used to reference this layout in `add_entry(row_style=...)`.
            html (str or HtmlElement): A string of HTML or an HtmlElement object with placeholders for substitution.
            is_default (bool, optional): If True, this style becomes the default for all subsequent entries.

        Side Effects:
            - Registers the style in `self._row_styles` under the given `name`.
            - Optionally updates `self._default_row_styles` if `is_default` is True.

        Example:
            card = self.add_card(title='Row Style Example')

            card.add_row_style('test', html=HtmlDiv([
                HtmlElement('span', contents=[
                    HtmlElement('h4', contents='{label}')
                ]),
                HtmlElement('span', contents='{value}')
            ]))

            card.add_entry(label='Custom Row', value='Styled Entry', row_style='test')
        """
        if not isinstance(html, str) and hasattr(html, 'render'):
            html = html.render()
        self._row_styles[name] = html
        if is_default:
            self._default_row_styles = name

    def set_default_style(self, name=None):
        """
        Sets the default row style to be used for entries that do not explicitly specify one.

        Args:
            name (str, optional): The name of the row style to set as default. Must exist in `self._row_styles`.

        Side Effects:
            - Updates `self._default_row_styles` to the given style name if it exists.
        """
        if name in self._row_styles:
            self._default_row_styles = name

    def get_field_value(self, value, field, label):
        """
        Internal method to resolve a field value, label, and field type from a given object.

        This is primarily used by `add_entry()` and related methods when `field` is specified but `value` is not.
        It handles:
          - Field traversal via double-underscore paths (e.g. `user__email`)
          - Multi-field tuples/lists
          - Field display methods (e.g. `get_status_display`)
          - Django model field type extraction via `_meta.get_field()`
          - Label fallback using `label_from_field()`

        Args:
            value (any): A pre-resolved value (if already known). If None, will attempt to resolve from `field`.
            field (str or list/tuple of str): The field name or path to resolve from `self.details_object`.
            label (str or None): Optional label. If not provided, one will be generated from the field name.

        Returns:
            tuple:
                value (any): The resolved value (or list of values if `field` is a list/tuple).
                label (str or None): A label for display purposes.
                field_type (Field or list of Field or None): The Django model field type(s), if available.

        Notes:
            - Normally called internally by entry rendering logic.
            - Uses `getattr()` for dynamic resolution and supports method calls (e.g. display methods).
            - Handles missing attributes and non-field values gracefully.
        """
        field_type = None
        if value is None and field is not None:
            if isinstance(field, (list, tuple)):
                values = []
                field_type = []
                for _field in field:
                    _value, _label, _field_type = self.get_field_value(value=None, field=_field, label=label)
                    if not label:
                        label = _label
                    values.append(_value)
                    field_type.append(_field_type)
                value = values
            else:
                details_object = self.details_object
                if details_object is not None:
                    value = details_object
                    old_value = None
                    parts = field.split('__')
                    try:
                        for part in parts:
                            old_value = value
                            value = getattr(value, part)
                    except AttributeError:
                        value = None

                    if old_value is not None and len(parts) > 0:
                        try:
                            field_type = old_value._meta.get_field(parts[-1])
                        except FieldDoesNotExist:
                            field_type = None
                        try:
                            value = getattr(old_value, f'get_{parts[-1]}_display')
                        except AttributeError:
                            pass
                    if not hasattr(value, 'through') and callable(value):
                        value = value()

                    if label is None:
                        label = self.label_from_field(field=field, field_type=field_type)
        return value, label, field_type

    def _add_many_to_many_field(self, label, query, query_filter=None, m2m_field=None,
                                html_barge=None, default='N/A', html_override=None,
                                entry_css_class=None, css_class=None, menu=None,
                                default_if=None, value_type=None, row_style=None, **kwargs):
        """
        Internal method for rendering many-to-many or reverse-related objects as an HTML badge list.

        This method is normally called indirectly by `add_entry()` when the value is a Django `ManyToManyManager`
        or reverse relation (i.e. when `hasattr(value, 'through')` is True). It outputs a row displaying each related
        object as a styled badge.

        Args:
            label (str): The label to display for the row.
            query (QuerySet or RelatedManager): The related manager to query related objects.
            query_filter (dict, optional): Optional filter applied to the query results.
            m2m_field (str, optional): Name of an attribute or method on each related object to display. If not set,
                                       the related object is stringified.
            html_barge (str, optional): HTML snippet for wrapping each item (default is a Bootstrap badge).
                                        Use `%1%` as a placeholder for the rendered value. The
                                        snippet is markup; the value put in it is escaped unless
                                        it is marked safe.
            default (str, optional): Fallback text if the relation is empty. Defaults to `'N/A'`.
            html_override (str, optional): Full HTML override for the entire value cell.
            entry_css_class (str, optional): CSS class for the value cell.
            css_class (str, optional): CSS class for the row container.
            menu (list, optional): Optional action menu for the row.
            default_if (callable, optional): Callable to determine if the default should be applied.
            value_type (str, optional): Optional rendering hint (`'m2m'`).
            row_style (str, optional): Optional named row style for layout customization.
            **kwargs: Any additional arguments passed through to `_add_entry_internal()`.

        Returns:
            dict: An entry dictionary suitable for adding to the card's row structure.

        Example (automatic via add_entry):
            card.add_entry(
                label='Assigned Tags',
                value=obj.tags,  # a ManyToMany manager or reverse relation
                m2m_field='name',  # optional: field or method to display
                value_type='m2m'  # optional: explicitly mark this as a many-to-many value
            )
        """

        if html_barge is None:
            # Spelled for this request's Bootstrap pack: the pill and the colour are named
            # differently in 4 and 5, and this is markup built in Python rather than in a
            # pack template. See cards.packs.
            html_barge = f'<span class="small {pack_class("m2m_badge", self.request)}"> %1% </span> '

        if query_filter is None:
            results = query.all()
        else:
            results = query.filter(**query_filter)
        html = ''
        for result in results:
            if m2m_field is None:
                value = result
                html += html_barge.replace('%1%', escape_value(value))
            else:
                if hasattr(result, m2m_field):
                    value = getattr(result, m2m_field)
                    if callable(value):
                        value = value()
                    html += html_barge.replace('%1%', escape_value(value))
        html = mark_safe(html)

        return self._add_entry_internal(label=label,
                                        value=html,
                                        default=default,
                                        html_override=html_override,
                                        entry_css_class=entry_css_class,
                                        css_class=css_class,
                                        menu=menu,
                                        default_if=default_if,
                                        value_type=value_type,
                                        row_style=row_style,
                                        **kwargs)

    def _add_entry_internal(self, value=None, field=None, label=None, default='N/A', link=None,
                            hidden=False, hidden_if_blank_or_none=None, hidden_if_zero=None, html_override=None,
                            value_method=None, value_type=None,
                            entry_css_class=None, css_class=None, row_css_class=None, menu=None,
                            default_if=None, row_style=None,
                            tooltip=None, value_link=None, css_class_method=None,
                            badge=None, icon=None, copy_to_clipboard=False, truncate=None,
                            prefix=None, suffix=None, placeholder=None, status_dot=None,
                            progress_bar=None, image=None, timestamp=False,
                            help_text=None, boolean_icon=False, popover=None, separator=False,
                            number_format=None, rating=None,
                            show_if=None, auto_link=False, sparkline=False, old_value=None,
                            **kwargs):
        """
        Internal method for creating a fully-resolved entry dictionary used in card rows.

        This is the central rendering engine behind `add_entry()` and related helpers. It handles:
          - Value and label resolution from a field (via `get_field_value`)
          - Conditional hiding (empty, zero, or flagged as hidden)
          - Type-based dispatch to boolean, date, or many-to-many renderers
          - Formatting logic (custom value methods, HTML overrides, merging)
          - Custom row styling via defined `row_style` templates
          - Optional link and menu rendering

        Args:
            value (any, optional): Direct value to display. If None, `field` will be used to resolve it.
            field (str, optional): Field name/path to resolve from `details_object` if value is not given.
            label (str, optional): Label to show next to the value. If None, will be inferred from `field`.
            default (str, optional): Fallback value if the resolved value is None or empty. Defaults to 'N/A'.
            link (str or callable, optional): Optional link to wrap the value.
            hidden (bool, optional): If True, the entry is skipped entirely.
            hidden_if_blank_or_none (bool, optional): If True, hides the entry when value is None or empty.
            hidden_if_zero (bool, optional): If True, hides the entry when value is 0.
            html_override (str, optional): Template HTML to use instead of the value. Use `%1%` as placeholder.
                The value put in it is escaped unless it is marked safe.
            value_method (callable, optional): Function to transform the value before rendering.
            value_type (str, optional): Optional rendering hint (e.g., 'boolean', 'currency', 'm2m').
            entry_css_class (str, optional): CSS class for the value cell.
            css_class (str, optional): CSS class for the overall row container.
            menu (list, optional): A list of menu items (converted to `HtmlMenu` if present).
            default_if (callable, optional): Function to determine if the default value should be used.
            row_style (str, optional): Named row style to use for custom layout rendering.
            **kwargs: Additional arguments used for formatting, merging, or row style substitution.

        Returns:
            dict or None:
                A fully constructed entry dictionary if visible and valid; None if skipped due to visibility rules.

        Example (indirect):
            Called automatically by:
                - `add_entry()`
                - `add_row()`
                - `add_rows()`
                - Any value auto-dispatching logic

        Notes:
            - This method supports merging multiple values (e.g., list or tuple) into a single string using `merge=True`.
            - Row styles can be defined using `add_row_style()` and referenced by name here.
        """

        value, label, field_type = self.get_field_value(value=value, field=field, label=label)

        if hidden_if_blank_or_none is None:
            hidden_if_blank_or_none = self.hidden_if_blank_or_none

        if hidden_if_zero is None:
            hidden_if_zero = self.hidden_if_zero

        if hidden or (hidden_if_blank_or_none and (value is None or value == '') or
                      (hidden_if_zero and isinstance(value, (float, int)) and value == 0)):
            return None

        if show_if is not None and callable(show_if):
            if self.details_object is not None and not show_if(self.details_object):
                return None

        if isinstance(value, bool):
            return self.add_boolean_entry(value=value,
                                          label=label,
                                          hidden=hidden,
                                          html_override=html_override,
                                          entry_css_class=entry_css_class,
                                          css_class=entry_css_class,
                                          menu=menu,
                                          default_if=default_if,
                                          value_type=value_type,
                                          row_style=row_style,
                                          **kwargs)
        elif isinstance(value, datetime.date):
            return self.add_date_entry(value=value,
                                       label=label,
                                       hidden=hidden,
                                       html_override=html_override,
                                       menu=menu,
                                       default_if=default_if,
                                       value_type=value_type,
                                       row_style=row_style,
                                       **kwargs)
        elif hasattr(value, 'through'):
            return self._add_many_to_many_field(label=label,
                                                query=value,
                                                default=default,
                                                html_override=html_override,
                                                entry_css_class=entry_css_class,
                                                css_class=entry_css_class,
                                                menu=menu,
                                                default_if=default_if,
                                                value_type=value_type,
                                                row_style=row_style,
                                                **kwargs)
        else:
            if value is None or value == '' or default_if:
                value = default
                is_default = True
            else:
                is_default = False

            if is_default and placeholder:
                if isinstance(placeholder, str):
                    value = placeholder
                entry_css_class = ((entry_css_class or '') + ' text-muted font-italic fst-italic').strip()

            if boolean_icon and not is_default and isinstance(value, bool):
                if value:
                    icon = 'fas fa-check text-success'
                else:
                    icon = 'fas fa-times text-danger'
                value = ''

            if number_format is not None and not is_default and isinstance(value, (int, float)):
                if isinstance(number_format, int) and not isinstance(number_format, bool):
                    value = f"{float(value):,.{number_format}f}"
                else:
                    value = f"{value:,}"

            if sparkline and isinstance(value, (list, tuple)) and len(value) > 1:
                nums = [float(v) for v in value if isinstance(v, (int, float))]
                if len(nums) > 1:
                    min_v, max_v = min(nums), max(nums)
                    rng = max_v - min_v or 1
                    w, h = 80, 20
                    if sparkline == 'bar':
                        bar_w = w / len(nums)
                        bars = ''.join(
                            f'<rect x="{i * bar_w}" y="{h - (v - min_v) / rng * h}" '
                            f'width="{bar_w * 0.8}" height="{(v - min_v) / rng * h}" fill="currentColor"/>'
                            for i, v in enumerate(nums)
                        )
                        value = mark_safe(f'<svg width="{w}" height="{h}" style="vertical-align:middle">{bars}</svg>')
                    else:
                        points = ' '.join(
                            f'{i * w / (len(nums) - 1)},{h - (v - min_v) / rng * h}'
                            for i, v in enumerate(nums)
                        )
                        value = mark_safe(
                            f'<svg width="{w}" height="{h}" style="vertical-align:middle">'
                            f'<polyline points="{points}" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>')

            multiple_parts = isinstance(value, (list, tuple))

            if value_method is not None:
                if multiple_parts:
                    value = [value_method(v) for v in value]
                else:
                    value = value_method(value)
            if value_type is not None or field_type is not None:
                if multiple_parts:
                    if isinstance(field_type, (list, tuple)):
                        value = [self.get_value_from_type(v, value_type, ft, is_default, **kwargs)
                                 for v, ft in zip(value, field_type)]
                    else:
                        value = [self.get_value_from_type(v, value_type, field_type,
                                                          is_default, **kwargs) for v in value]
                else:
                    value = self.get_value_from_type(value, value_type, field_type, is_default, **kwargs)
            # html_override and merge_string are the caller's markup, and the value put into
            # them is escaped unless it is marked safe -- the result is markup either way.
            if html_override is not None:
                if multiple_parts:
                    value = [mark_safe(html_override.replace('%1%', escape_value(v))) for v in value]
                else:
                    value = mark_safe(html_override.replace('%1%', escape_value(value)))

            if multiple_parts and kwargs.get('merge', False):
                merge_string = kwargs.get('merge_string', ' ')
                multiple_parts = False
                value = mark_safe(merge_string.join(['' if x is None else escape_value(x) for x in value]))

            if menu is not None and isinstance(menu, (list, tuple)):
                menu = HtmlMenu(self.request, self.button_menu_type).add_items(*menu)
            row_style_html = None
            if (row_style is not None and row_style in self._row_styles) or self._default_row_styles is not None:

                if row_style is not None:
                    html_row_style = self._row_styles[row_style]
                else:
                    html_row_style = self._row_styles[self._default_row_styles]

                value_dict = {'value': value,
                              'label': label,
                              'link': link,
                              **kwargs}
                if menu is not None:
                    value_dict['menu'] = menu.render()
                # The style is the caller's markup; what fills it is escaped unless it is
                # marked safe, as {{ }} would print it. See _RowStyleFormatter.
                row_style_html = mark_safe(_row_style_formatter.vformat(html_row_style, (), value_dict))

            if css_class_method is not None:
                css_class = css_class_method(value)

            if timestamp and isinstance(value, (datetime.datetime, datetime.date)):
                if not tooltip:
                    fmt = '%Y-%m-%d %H:%M:%S' if isinstance(value, datetime.datetime) else '%Y-%m-%d'
                    tooltip = value.strftime(fmt)
                value = timesince(value) + ' ago'

            if truncate is not None and not auto_link and isinstance(value, str) and len(value) > truncate:
                if not tooltip:
                    tooltip = value
                value = value[:truncate] + '\u2026'

            if auto_link and isinstance(value, str):
                # Escaped first, so that the only markup in the result is the links.
                value = escape_value(value)
                value = re.sub(r'(https?://\S+)', r'<a href="\1" target="_blank">\1</a>', value)
                value = re.sub(r'(?<!["\'/=])(\b[\w.+-]+@[\w-]+\.[\w.-]+\b)', r'<a href="mailto:\1">\1</a>', value)
                value = mark_safe(value)

            if badge is True:
                # The colour half of `class="badge ..."`, which the pack spells its own way:
                # Bootstrap 5's text-bg- picks a contrasting foreground where 4's badge-
                # carried one of its own.
                badge = pack_class('entry_badge', self.request)

            if progress_bar is True:
                progress_bar = 'bg-primary'
            if progress_bar and not _is_percentage(value):
                # The value is written into `style="width:...%"` as well as shown, and escaping
                # leaves a semicolon alone there -- so a value that is not a number draws no bar,
                # only the value. A progress bar is a number or nothing.
                progress_bar = None

            if image is True:
                image = '40px'

            if popover is not None:
                if isinstance(popover, str):
                    popover = {'content': popover, 'title': ''}

            rating_range = None
            if rating is not None:
                if rating is True:
                    rating = 5
                rating_range = list(range(rating))

            if old_value is not None:
                if number_format is not None and isinstance(old_value, (int, float)):
                    if isinstance(number_format, int) and not isinstance(number_format, bool):
                        old_value = f"{float(old_value):,.{number_format}f}"
                    else:
                        old_value = f"{old_value:,}"
                else:
                    old_value = str(old_value)

            entry = {'label': label,
                     'html': value,
                     'entry_css_class': entry_css_class,
                     'css_class': css_class or '',
                     'row_css_class': row_css_class or '',
                     'multiple_lines': multiple_parts,
                     'link': link,
                     'tooltip': tooltip,
                     'value_link': value_link,
                     'badge': badge,
                     'icon': icon,
                     'copy_to_clipboard': copy_to_clipboard,
                     'menu': menu,
                     'row_style_html': row_style_html,
                     'prefix': prefix,
                     'suffix': suffix,
                     # Written into a style attribute by the row templates: checked, not escaped.
                     'status_dot': css_colour(status_dot),
                     'progress_bar': progress_bar,
                     'image': image,
                     'help_text': help_text,
                     'popover': popover,
                     'separator': separator,
                     'rating': rating,
                     'rating_range': rating_range,
                     'old_value': old_value,
                     **kwargs}
            return entry

    def get_value_from_type(self, value, value_type, field_type, is_default, **kwargs):
        """
        Hook method for transforming a value based on its type before rendering.

        This method can be overridden in subclasses to apply formatting or conversions
        for specific `value_type`s or Django `field_type`s.

        Args:
            value (any): The raw value to transform.
            value_type (str): An explicit type hint (e.g., 'currency', 'percent', etc.).
            field_type (Field): The Django model field instance, if available.
            is_default (bool): Whether the value is a default fallback rather than real data.
            **kwargs: Additional context passed from the entry logic.

        Returns:
            any: The transformed value, or the original value by default.

        Example:
            def get_value_from_type(self, value, value_type, field_type, is_default, **kwargs):
                if value_type == 'currency':
                    return f"£{value:,.2f}"
                return super().get_value_from_type(value, value_type, field_type, is_default, **kwargs)
        """
        return value

    def process_data(self):
        """
        Internal method that populates card content depending on its group type.

        For datatable-type cards, this initializes the datatable (if not already set), attaches it
        to `self.extra_card_info`, and calls the appropriate `setup_table_*` method on the view.

        For standard cards with `call_details_data=True`, it attempts to call a view method to load
        additional content (e.g., `get_<code>_data()` or `get_details_data()`).

        Behavior:
            - CARD_TYPE_DATATABLE / CARD_TYPE_ORDERED_DATATABLE:
                - Initializes the table using `add_table()` or `add_ordered_table()`.
                - Attaches it to `self.extra_card_info['datatable']`.
                - Looks up a table setup method on the view:
                    * `setup_table_<custom>` (if `setup_table` key is set)
                    * `setup_table_<code>` (fallback if available)
                    * `setup_table` (default)
                - Adds the table to `view.tables[code]` if that dict exists.

            - CARD_TYPE_STANDARD:
                - If `call_details_data` is True:
                    * Tries to call `get_<code>_data(card, details_object)` if defined on the view.
                    * Otherwise falls back to `get_details_data(card, details_object)`.

        Side Effects:
            - Mutates `self.extra_card_info` and potentially `self.view.tables`.

        Notes:
            - This method is called internally, usually during rendering or card setup.
            - Assumes `self.view` has the required setup/data methods.
        """
        if (self.group_type in (CARD_TYPE_DATATABLE, CARD_TYPE_ORDERED_DATATABLE) and
                self.extra_card_info['datatable'] is None):

            datatable_model = self.extra_card_info['datatable_model']
            table_id = self.extra_card_info['datatable_id']
            if self.extra_card_info['datatable'] is None:
                if self.group_type == CARD_TYPE_ORDERED_DATATABLE:
                    table = self.add_ordered_table(table_id=table_id,
                                                   model=datatable_model,
                                                   order_field=self.extra_card_info['order_field'])
                else:
                    table = self.add_table(table_id=table_id, model=datatable_model)
                self.extra_card_info['datatable'] = table
            else:
                table = self.extra_card_info['datatable']
            setup_table_field = 'setup_table'
            if self.extra_card_info['setup_table'] is not None:
                field_setup_table_field = f'setup_table_{self.extra_card_info["setup_table"]}'
                if hasattr(self.view, field_setup_table_field):
                    setup_table_field = field_setup_table_field
            elif self.code is not None:
                field_setup_table_field = f'setup_table_{self.code}'
                if hasattr(self.view, field_setup_table_field):
                    setup_table_field = field_setup_table_field

            getattr(self.view, setup_table_field)(details_object=self.details_object, table=table)
            if hasattr(self.view, 'tables'):
                self.view.tables[self.code] = table
        elif self.group_type == CARD_TYPE_LINKED_DATATABLES:
            self._process_linked_datatables()
        elif self.group_type == CARD_TYPE_ACCORDION:
            self._process_accordion()
        elif self.group_type == CARD_TYPE_STANDARD and self.call_details_data:
            if self.code is not None and hasattr(self.view, f'get_{self.code}_data'):
                getattr(self.view, f'get_{self.code}_data')(card=self, details_object=self.details_object)
            elif hasattr(self.view, 'get_details_data'):
                getattr(self.view, 'get_details_data')(card=self, details_object=self.details_object)

    def _process_linked_datatables(self):
        """Initialize all datatables for a linked datatables card."""
        datatables_config = self.extra_card_info.get('datatables', [])
        initialized_tables = []
        total = len(datatables_config)

        for i, dt_config in enumerate(datatables_config):
            table_id = dt_config['id']
            model = dt_config['model']
            title = dt_config.get('title', table_id.replace('_', ' ').title())
            linked_field = dt_config.get('linked_field')
            css_class = dt_config.get('css_class', '')

            table = DatatableTable(table_id=table_id, model=model, view=self.view)

            setup_table_field = f'setup_table_{table_id}'
            if hasattr(self.view, setup_table_field):
                getattr(self.view, setup_table_field)(details_object=self.details_object, table=table)

            # Add arrow column to tables that link to the next table or to a page
            row_link = dt_config.get('row_link')
            if i < total - 1 or row_link:
                arrow_col = ColumnBase(column_name='_arrow', field=None, table=table, model=model)
                arrow_col.title = ''
                arrow_col.options['calculated'] = True
                arrow_col.column_defs['orderable'] = False
                arrow_col.column_defs['className'] = 'linked-dt-arrow'
                arrow_col.column_defs['width'] = '30px'
                arrow_col.row_result = lambda data_dict, page_results: '\u25B6'
                table.columns.append(arrow_col)

            # First table loads data normally; subsequent linked tables start empty
            if i > 0 and linked_field:
                table.ajax_data = False
                table.table_data = []

            if hasattr(self.view, 'tables'):
                self.view.tables[table_id] = table

            if row_link:
                from django_datatables.helpers import get_url, DUMMY_ID
                row_link_url = get_url(row_link)
            else:
                row_link_url = None

            menu = dt_config.get('menu')
            if menu and not isinstance(menu, HtmlMenu):
                html_menu = HtmlMenu(self.request, 'button_group')
                html_menu.add_items(*menu)
                menu = html_menu

            initialized_tables.append({
                'table': table,
                'id': table_id,
                'title': title,
                'linked_field': linked_field,
                'css_class': css_class,
                'index': i,
                'row_link': row_link_url,
                'menu': menu,
            })

        self.extra_card_info['initialized_tables'] = initialized_tables

    def _process_accordion(self):
        """Initialize accordion panels. Each panel contains a card rendered as its body content."""
        panels_config = self.extra_card_info.get('panels', [])
        initialized_panels = []

        for i, panel in enumerate(panels_config):
            panel_id = panel.get('id', f'{self.code}_panel_{i}')
            title = panel.get('title', f'Panel {i + 1}')
            expanded = panel.get('expanded', i == 0)
            icon = panel.get('icon')
            header_css_class = panel.get('header_css_class', '')
            ajax_load = panel.get('ajax_load', False)
            card = panel.get('card')

            initialized_panels.append({
                'id': panel_id,
                'title': title,
                'expanded': expanded,
                'icon': icon,
                'header_css_class': header_css_class,
                'ajax_load': ajax_load,
                'card': card,
                'index': i,
            })

        self.extra_card_info['initialized_panels'] = initialized_panels

    def add_table(self, model, table_id=None):
        """
        Internal helper to create and attach a standard (non-orderable) datatable to the card.

        Args:
            model (Model): The Django model backing the table.
            table_id (str, optional): Optional identifier for the datatable instance.

        Returns:
            DatatableTable: The constructed datatable instance (with `ajax_data` set to False).

        Side Effects:
            - Sets `self.extra_card_info['datatable']` to the new table.
        """
        table = DatatableTable(table_id=table_id, model=model, view=self.view)
        self.extra_card_info['datatable'] = table
        table.ajax_data = False
        return table

    def add_ordered_table(self, model, order_field, table_id=None):
        """
        Internal helper to create and attach an ordered datatable with drag-and-drop support.

        Args:
            model (Model): The Django model to be rendered in the table.
            order_field (str): The field used to determine row ordering (e.g., 'order').
            table_id (str, optional): Optional identifier for the table.

        Returns:
            OrderedDatatable: The constructed ordered datatable with reorder plugin enabled.

        Side Effects:
            - Adds the `Reorder` plugin to the table.
            - Sets `self.extra_card_info['datatable']` to the new table.
            - Disables `ajax_data`.
        """
        table = OrderedDatatable(table_id=table_id,
                                 model=model,
                                 view=self.view,
                                 order_field=order_field)
        table.add_plugin(Reorder)
        table.ajax_data = False
        self.extra_card_info['datatable'] = table
        return table

    def get_created_modified_dates(self, details_object):
        """
        Returns the created and modified timestamps from the given object, if available and enabled.

        This method checks whether `show_created_modified_dates` is enabled and whether the
        `details_object` has `created` and `modified` attributes. If so, it returns them as a tuple.

        Args:
            details_object (object): The object from which to retrieve the `created` and `modified` timestamps.

        Returns:
            tuple[datetime, datetime] or None:
                A tuple containing (created, modified) if available; otherwise, None.
        """
        if (self.show_created_modified_dates and details_object and
                hasattr(details_object, 'created') and hasattr(details_object, 'modified')):
            return details_object.created, details_object.modified
        return None

    def datatable_sort(self, **kwargs):
        """
        Updates the order of rows in an ordered datatable based on a new sort sequence.

        This method is typically called after a "Move Up" / "Move Down" action in the UI,
        where the frontend sends a list of new positions for items in the table.

        Args:
            **kwargs:
                sort (list of tuples): A list of (new_order, object_id) pairs representing the updated order.

        Example:
            kwargs['sort'] = [
                (1, 42),  # Object with ID 42 should now be first
                (2, 37),  # Object with ID 37 should now be second
                ...
            ]

        Behavior:
            - Fetches current `order_field` values for the specified IDs.
            - Compares current values to the desired new order.
            - Updates and saves objects where the order has changed.

        Notes:
            - Requires `self.extra_card_info['order_field']` to be set (e.g. 'order').
            - `self.extra_card_info['datatable_model']` must be the model class for the table.
            - Minimizes writes by only updating rows where the order actually differs.
        """
        order_field = self.extra_card_info['order_field']
        ids = [x[1] for x in kwargs['sort']]
        current_sort = dict(self.extra_card_info['datatable_model'].objects.filter(id__in=ids).
                            values_list('id', order_field))
        for s in kwargs['sort']:
            if current_sort.get(s[1]) != s[0]:
                o = self.extra_card_info['datatable_model'].objects.get(id=s[1])
                setattr(o, order_field, s[0])
                o.save()

    @staticmethod
    def label_from_field(field, field_type):
        """
        Generates a human-readable label from a field name or type.

        This utility is typically used to auto-generate labels for fields when one is not explicitly provided.

        Args:
            field (str or any): The field name, usually a string. Can include slashes or double underscores.
            field_type (Field, optional): A Django model field or similar object. If it has a `verbose_name`,
                                          that is used as the label (capitalized).

        Returns:
            str: A human-readable label derived from the field name or verbose name.

        Examples:
            label_from_field("user__email", None)       # → "Email"
            label_from_field("created_at", None)        # → "Created At"
            label_from_field("camelCaseField", None)    # → "Camel Case Field"
        """
        if field_type is not None and hasattr(field_type, 'verbose_name') and field_type.verbose_name is not None:
            return field_type.verbose_name.capitalize()
        elif type(field) == str and len(field) > 0:
            field_no_path = field.split('/')[-1].split('__')[-1]
            if field_no_path.find('_') > 0:
                return field_no_path.replace('_', ' ').title()
            else:
                title = field_no_path[0].upper()
                for letter in field_no_path[1:]:
                    if letter.isupper():
                        title += ' '
                    title += letter
                return title

    def add_rows(self, *args, default='N/A', hidden=False, extra_row_kwargs=None):
        """
        Adds multiple rows to the card in a flexible, declarative format.

        Each argument can be:
          - A string: treated as a field name (used to fetch from `details_object`).
          - A dict: passed as keyword arguments to `add_entry()`, with support for per-entry overrides.
          - A list or tuple: passed directly to `add_row()` for manual row construction.

        Common options like `default` and `hidden` are applied to all entries unless overridden.

        Args:
            *args: Variable-length list of fields, dicts, or (args) for `add_row()`.
            default (str, optional): Default value to display if no value is found. Defaults to 'N/A'.
            hidden (bool, optional): Whether to hide the entry/row if not overridden per-entry.
            extra_row_kwargs (dict, optional): Additional kwargs applied to each entry (unless overridden).

        Example:
            card.add_rows(
                'name',
                {'field': 'email', 'label': 'Email Address'},
                ('first_name', 'last_name'),  # calls add_row with multiple fields
                default='Not available',
                extra_row_kwargs={'entry_css_class': 'text-muted'}
            )
        """
        if extra_row_kwargs is None:
            extra_row_kwargs = {}
        for arg in args:
            if isinstance(arg, str):
                self.add_entry(field=arg, default=default, hidden=hidden, **extra_row_kwargs)
            elif isinstance(arg, dict):
                if 'default' not in arg:
                    arg['default'] = default
                if 'hidden' not in arg:
                    arg['hidden'] = hidden
                self.add_entry(**arg, **extra_row_kwargs)
            elif isinstance(arg, (list, tuple)):
                self.add_row(*arg)

    def add_tiles(self, tiles, empty_message=None, width=None):
        """Render the card's body as a grid of small tiles, one per object.

        The tile equivalent of add_entry/add_rows: where those draw label/value rows, this
        draws a wrapping row of small bordered cards, each with a heading, an optional
        subheading, a few meta lines, an optional image, an optional badge and an edit
        pencil. It is the shape `add_link_gallery_card` renders for links, for any object::

            card = self.add_card('colours', title='Colours & Finishes')
            card.add_tiles(
                [Tile(key=f'colour_finish_{cf.pk}',
                      heading=cf.colour.name,
                      subheading=cf.finish.name,
                      meta=[cf.price_display,
                            ('none in stock', 'text-danger') if not cf.stock else f'{cf.stock} in stock'],
                      edit_url=cf.modal_url,
                      badge='Default' if cf.is_default else None)
                 for cf in colour_finishes],
                empty_message='No colours or finishes yet. Use Add above to add one.',
                width='150px',
            )

        Everything a tile shows is escaped except `Tile.heading_html` -- see :class:`Tile`.

        The card renders through the `tiles` template, which this sets: a template_name given
        to add_card() is replaced, because the tiles are body content that only this template
        draws. Called more than once, it adds to the grid rather than replacing it.

        Args:
            tiles (list): :class:`Tile` objects, or dicts of the same fields.
            empty_message (str, optional): Shown in place of the grid when there are no tiles.
                Nothing is drawn without one.
            width (str, optional): The width of one tile, as a CSS length. Defaults to the
                stylesheet's 150px. Worth setting for a tile holding something that must not
                wrap -- a two-part measurement, say.

        Returns:
            CardBase: The card, so the call can be chained onto add_card().
        """
        self.extra_card_info.setdefault('tiles', []).extend(Tile.build(tile) for tile in tiles)
        if empty_message is not None:
            self.extra_card_info['tiles_empty_message'] = empty_message
        if width is not None:
            self.extra_card_info['tiles_width'] = width
        self.template_name = 'tiles'
        self.requires_card_css = True
        return self

    def add_banner_tiles(self, tiles, empty_message=None, width=None, slider=None):
        """Render the card's body as a grid of :class:`BannerTile` cards.

        The card it is called on is the master card -- its header, menu and footer stay as
        they are -- and each tile is a card of its own inside it::

            card = self.add_card('training', title='Your training')
            card.add_banner_tiles(
                [BannerTile(key=f'course_{c.pk}', title=c.name, description=c.summary,
                            banner_label=c.category.name, banner_icon=c.category.icon,
                            step=f'Step {n} of {len(courses)}',
                            stats=[('fas fa-play-circle', f'{c.lessons} lessons')],
                            progress=c.progress_for(user), status=c.status_for(user),
                            action_label='Start', action_url=c.get_absolute_url())
                 for n, c in enumerate(courses, 1)],
                empty_message='No courses assigned yet.',
            )

        ``slider=True`` puts the tiles in one horizontal, swipeable row instead of a grid,
        with prev/next arrows and a dot per tile -- the shape for ``layout='feature'``
        promotions, though any layout can be a slide.

        A learning path at the head of the grid is a ``BannerTile(layout='highlight')`` first
        in the list. A single course on its own is the same call with one tile; pass ``border='none'`` to
        add_card() as well to drop the master card's box around it.

        Like add_tiles, this sets the card's template (replacing any template_name given to
        add_card()), and called more than once it adds to the grid.

        Args:
            tiles (list): :class:`BannerTile` objects, or dicts of the same fields.
            empty_message (str, optional): Shown in place of the grid when there are no tiles.
            width (str, optional): The width of one tile, as a CSS length. Defaults to the
                stylesheet's 260px. A feature tile's width is set by the stylesheet instead.
                It is written into a ``style`` attribute, so it must come from code.
            slider (bool, optional): True lays the tiles out as a slider, False as a grid.
                Left as None, it keeps what an earlier call set (a grid if none did).

        Returns:
            CardBase: The card, so the call can be chained onto add_card().
        """
        # Build them all before changing anything, so one bad tile leaves the card as it was.
        tiles = [BannerTile.build(tile) for tile in tiles]
        if slider is not None:
            self.extra_card_info['banner_tiles_slider'] = bool(slider)
        self.extra_card_info.setdefault('banner_tiles', []).extend(tiles)
        # What the template draws, worked out once: a slider only when there is something to
        # slide, so an empty one is just the empty message.
        self.extra_card_info['banner_tiles_is_slider'] = bool(
            self.extra_card_info.get('banner_tiles_slider') and self.extra_card_info['banner_tiles'])
        if empty_message is not None:
            self.extra_card_info['banner_tiles_empty_message'] = empty_message
        if width is not None:
            self.extra_card_info['banner_tiles_width'] = width
        self.template_name = 'banner_tiles'
        self.requires_card_css = True
        return self

    def add_sections(self, cards):
        """Make this card's body a stack of folding sections, one per card in ``cards``.

        For a record's sidebar -- contact, site, tags, priority -- where each part is a card of its
        own but a page of full cards is too much: each becomes a header the reader can fold, its
        title and menu taken from the card, its body the card's without its header::

            card = self.add_card('customer', title='Customer')
            card.add_sections([contact_card, site_card, tags_card])

        A card added empty (``add_card(is_empty=True)``) or ``collapsed=True`` starts folded.
        ``None`` entries are skipped, and a dict of :class:`CardSection` fields
        (``{'card': c, 'folded': True}``) sets a section's title, menu or folding by hand. A card
        that is not one, a section with no title to name its toggle, or a card that already has a
        body of its own (empty, rows, a datatable) raises here, before any card is changed. Each
        card becomes its section's: its own header and collapse are switched off, so it is not
        shown elsewhere on the page too. The sections fold in the browser and do not remember it
        across page loads; opening one re-measures its own datatables and fires a bubbling
        ``django-cards:section-toggle`` event on the section.

        Like add_banner_tiles, this sets the card's template (replacing any template_name given to
        add_card()) -- the pack's html card, its body the stack -- and called more than once it
        adds to the stack. Chrome is in ``cards/css/cards.css`` (``.django-card__section*``).

        Returns:
            CardBase: The card, so the call can be chained onto add_card().
        """
        if self.template_name != 'section_stack':
            # What the card already is would be dropped for the stack without a word: an empty
            # card's message, a datatable registered on the view but never drawn, its own rows.
            if self.is_empty or self.group_type != CARD_TYPE_STANDARD or self.rows:
                raise ValueError(f'add_sections() makes a card\'s body its stack, and card {self.code!r} '
                                 f'already has one (empty, rows, or not a standard card)')
        # Built and checked before any card is claimed, so a bad entry or a clash changes nothing.
        sections = build_sections(cards, claim=False)
        taken = set(getattr(self.view, 'cards', None) or {})
        seen = set()
        for section in sections:
            stacked = section.card
            if stacked is self or _stack_holds(stacked, self):
                raise ValueError(f'Card {self.code!r} cannot hold a stack that holds itself')
            if id(stacked) in seen or getattr(stacked, 'section', None) is not None:
                raise ValueError(f'Card {stacked.code!r} is in a section stack already; a card is in one '
                                 f'place on a page, or its DOM ids are there twice')
            seen.add(id(stacked))
            clash = section.ids & taken
            if clash:
                raise ValueError(f'Section ids {sorted(clash)} are card names on this view')
        for section in sections:
            section.claim()
        self.extra_card_info.setdefault('sections', []).extend(sections)
        # Read (and called) by the html card template, so the sections' cards are drawn when
        # this card is, after cards_ready(), and once.
        self.extra_card_info['html'] = _SectionsHtml(self).render
        self.template_name = 'section_stack'
        self.requires_card_css = True
        return self

    def get_export_data(self):
        data = []
        for row in self.rows:
            if row.get('type') == 'html':
                continue
            for entry in row.get('entries', []):
                label = entry.get('label', '')
                value = entry.get('html', '')
                if isinstance(value, str):
                    value = re.sub(r'<[^>]+>', '', value)
                elif isinstance(value, (list, tuple)):
                    value = ', '.join(re.sub(r'<[^>]+>', '', str(v)) for v in value)
                else:
                    value = str(value)
                data.append({'label': label or '', 'value': value})
        return data

    def _render_template(self, override_card_context=None):
        extra_card_context = self.extra_card_context
        context = {'card': self,
                   'request': self.request,
                   'card_types': {'standard': CARD_TYPE_STANDARD,
                                  'datatable': CARD_TYPE_DATATABLE,
                                  'ordered_datatable': CARD_TYPE_ORDERED_DATATABLE,
                                  'html': CARD_TYPE_HTML},
                   'show_header': self.show_header,
                   }

        if self.exportable:
            context['export_data'] = json.dumps(self.get_export_data())

        if extra_card_context is not None:
            context = {**context, **extra_card_context}
        if override_card_context is not None:
            context = {**context, **override_card_context}

        template_name = self.template_name
        if template_name is None:
            template_name = self.template_defaults.get(self.group_type)

        if template_name in self.templates:
            template = self.templates[template_name]['name']
            if 'context' in self.templates[template_name]:
                context = {**self.templates[template_name]['context'], **context}
        else:
            template = template_name

        if self.border:
            border_class = CARD_BORDER_CSS_CLASSES[self.border]
            context['card_css_class'] = f"{context.get('card_css_class', '')} {border_class}".strip()

        # Straight to the pack's copy where the flat name is cards' own forwarder; see
        # cards.packs.resolve_template.
        html = render_to_string(resolve_template(template, self.request), context)
        if self.border or self.requires_card_css:
            html = card_css_once(self.request) + html
        return mark_safe(html)

    def render(self, override_card_context=None):
        """
        Renders the card as an HTML string using the appropriate template and context.

        When ajax_reload is enabled, wraps the output in a container div that serves
        as the stable target for AJAX content replacement.
        """
        html = self._render_template(override_card_context)
        if self.ajax_reload:
            return mark_safe(f'<div id="{self.code}_ajax">{html}</div>')
        return html

    def add_child_card_group(self, *args, div_css_class='', div_inner_css_class='',
                             div_inner_css='', override_card_context=None):
        """
        Adds a group of child cards to a layout- or group-style card.

        This method is only valid for cards with `group_type` set to `CARD_TYPE_CARD_GROUP` or `CARD_TYPE_CARD_LAYOUT`.
        It defines a logical grouping of cards for rendering within a layout card, with optional CSS classes
        and per-card context overrides.

        Args:
            *args: One or more card instances to include in the child group.
            div_css_class (str, optional): CSS class applied to the outer wrapper div of the group.
            div_inner_css_class (str, optional): CSS class applied to the inner wrapper div around the cards.
            div_inner_css (str, optional): Inline CSS styles for the inner wrapper div.
            override_card_context (dict, optional): Optional context overrides for each child card.

        Raises:
            Exception: If the card is not a layout- or group-type card.

        Side Effects:
            - Appends a dictionary to `self.child_card_groups` representing the child group configuration.

        Example:
            layout_card = self.add_layout_card()

            layout_card.add_child_card_group(
                child_1_card,
                div_css_class='col-6 float-left',
                div_inner_css='border-style: solid; border-color: red',
                override_card_context={'item_css': 'color: blue'}
            )

            layout_card.add_child_card_group(
                child_2_card,
                div_css_class='col-6 float-left'
            )
        """
        if self.group_type not in [CARD_TYPE_CARD_GROUP, CARD_TYPE_CARD_LAYOUT]:
            raise Exception('This will only work for card group')
        self.child_card_groups.append({'div_css_class': div_css_class,
                                       'div_inner_css_class': div_inner_css_class,
                                       'div_inner_css': div_inner_css,
                                       'cards': args,
                                       'override_card_context': override_card_context})
