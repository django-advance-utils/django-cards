import functools
import json

from django import template
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from cards.packs import pack_classes, pack_template, resolve_template, template_pack
from cards.panel_layout import SLOT_MARKER
from cards.render_scope import get_render_scope

register = template.Library()

TREEGRID_SHARED_ASSETS_MARK = '_treegrid_shared_assets_rendered'


@register.simple_tag(takes_context=True)
def pack_source(context, name):
    """Render the Bootstrap pack's copy of a template, in this template's own context.

    Every file under cards/standard/ that carries Bootstrap markup is one of these, and the
    markup itself lives in cards/bootstrap4/ and cards/bootstrap5/. The flat path stays the
    name projects use -- in an {% include %}, in a CardBase.templates subclass, or as the
    path they override -- and this picks the version behind it. See cards.packs.
    """
    return mark_safe(pack_template(name, context.get('request')).render(context.flatten()))


@register.simple_tag(takes_context=True)
def pack_path(context, name):
    """The template an {% include %} of the flat ``name`` should load: the pack's copy, or a
    project's override at the flat path. Used as ``{% pack_path '...' as t %}{% include t %}``
    so the include stays Django's own -- ``with`` and recursion work as before -- while
    skipping the forwarder. See cards.packs.resolve_template.
    """
    return resolve_template(name, context.get('request'))


@register.simple_tag(takes_context=True)
def pack_name(context):
    """The pack this request renders with, for handing to JavaScript."""
    return template_pack(context.get('request'))


@register.simple_tag(takes_context=True)
def pack_classes_json(context):
    """The pack's class strings as a JSON object, for a script that builds its own markup."""
    return mark_safe(json.dumps(pack_classes(context.get('request'))))


@register.simple_tag
def show_card(card, override_card_context=None):
    if override_card_context is None or override_card_context == '':
        html = card.render()
    else:
        html = card.render(override_card_context)
    return mark_safe(html)


@functools.lru_cache(maxsize=None)
def _shared_assets_cached():
    return render_to_string('cards/standard/_treegrid_shared.html')


def _shared_assets_html():
    """The shared half, rendered once per process.

    It is template-variable-free, so its rendered form is a process constant -- no point
    re-building ~110 KiB of it per request. Under DEBUG it renders fresh each time, so an
    edited template (or a project override dropped in mid-development) shows up without a
    restart.

    That makes context-freedom a requirement of any project override of
    _treegrid_css.html or _treegrid_script.html, not just a property of the package's own:
    the first served request's render is frozen for the life of the process, so an override
    carrying {% trans %}, a request value or anything else that varies would serve that
    first request's version -- its language, its user -- to everyone after it.
    """
    if settings.DEBUG:
        return render_to_string('cards/standard/_treegrid_shared.html')
    return _shared_assets_cached()


@register.simple_tag(takes_context=True)
def treegrid_shared_assets(context):
    """The treegrid stylesheet and behaviour, emitted once for the whole page.

    Every treegrid card needs the same ~110 KiB of it, so the first card on the page carries
    it and the rest emit only their own config.

    The request cycle is what counts as "the page", taken from cards.render_scope so that a
    card built without a request -- a form widget builds its own card mixin, and a modal can
    hold four of them -- is covered too. With nothing to mark, the shared half is carried
    again: the browser already has it, and the assignment guard in _treegrid_script.html makes
    the second copy a no-op. A card reloaded over ajax, or a modal body, is a request of its
    own and so carries it again for the same reason.

    The mark is set only once the shared half has actually rendered, so a broken template
    override raises on every card instead of raising once and silently starving the rest of
    the page. One limit is worth knowing: the mark records "rendered during this request",
    not "delivered to the browser" -- a treegrid rendered into output the caller then drops
    (a card group the page template never outputs, a fragment built and discarded) still
    consumes the page's emission, and the grids that do reach the browser then queue their
    configs and report the missing shared half on the console.
    """
    holder = get_render_scope() or context.get('request')
    if holder is not None and getattr(holder, TREEGRID_SHARED_ASSETS_MARK, False):
        return ''
    html = _shared_assets_html()
    if holder is not None:
        setattr(holder, TREEGRID_SHARED_ASSETS_MARK, True)
    return mark_safe(html)


@register.simple_tag
def panel_slot():
    """Where a panel layout leaves room for the page's own content, inside a card's own template.

    For a slot that is not a region or tab of its own -- the page's content inside a card's body,
    under something the card draws itself. ``PanelLayout.render_around`` splits the layout here.
    Not in a card that reloads over ajax: its reload would replace the page's content too.
    """
    return mark_safe(SLOT_MARKER)


class PanelLayoutAroundNode(template.Node):
    child_nodelists = ('nodelist',)

    def __init__(self, layout, nodelist):
        self.layout = layout
        self.nodelist = nodelist

    def render(self, context):
        layout = self.layout.resolve(context)
        if not hasattr(layout, 'render_around'):
            raise template.TemplateSyntaxError(
                f'panel_layout_around needs a PanelLayout; {self.layout.token!r} is {layout!r}')
        parts = layout.render_around()
        return mark_safe(f'{parts.before}{self.nodelist.render(context)}{parts.after}')


@register.tag
def panel_layout_around(parser, token):
    """``{% panel_layout_around layout %}...{% endpanel_layout_around %}``: the layout, with what is
    between the tags in its slot (``PanelLayout.render_around``).

    Whatever is inside renders in the page's own context, ``{% block %}`` tags included, so a base
    template can wrap every child page's content in the layout.
    """
    bits = token.split_contents()
    if len(bits) != 2:
        raise template.TemplateSyntaxError(f'{bits[0]} takes one argument, the PanelLayout')
    nodelist = parser.parse(('endpanel_layout_around',))
    parser.delete_first_token()
    return PanelLayoutAroundNode(parser.compile_filter(bits[1]), nodelist)
