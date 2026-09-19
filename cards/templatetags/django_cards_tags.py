import functools
import json

from django import template
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from cards.packs import pack_classes, pack_template, template_pack
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
