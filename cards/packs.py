"""Which Bootstrap the cards render for, and where the templates for it live.

Cards ships one folder of templates per supported Bootstrap version:

    cards/templates/cards/bootstrap4/
    cards/templates/cards/bootstrap5/

``DJANGO_CARDS_TEMPLATE_PACK`` picks between them, defaulting to Bootstrap 4:

    DJANGO_CARDS_TEMPLATE_PACK = 'bootstrap5'

It may instead be a dotted path to a callable taking the request and returning a pack name,
for a project that has to serve both -- the example app uses that to put a version toggle in
its nav bar. A pack name never contains a dot, which is what tells the two apart.

The flat paths stay the public names
------------------------------------
django-menus, which this follows, ships nothing at its flat template paths and resolves
``select_template([flat, pack])`` so a project override still wins. Cards cannot: projects
reference ``cards/standard/*.html`` directly -- in a ``CardBase.templates`` subclass, in
``{% include %}`` lines inside their own copies of a card template, and in overrides that
sit at the flat path. So every pack template keeps a file at its old flat path, holding one
``{% pack_source %}`` tag that renders the pack's copy:

    cards/standard/default.html          {% pack_source 'standard/default.html' %}
    cards/bootstrap4/standard/default.html   the Bootstrap 4 markup
    cards/bootstrap5/standard/default.html   the Bootstrap 5 markup

A project's own file at ``cards/standard/default.html`` still shadows the forwarder -- the
DIRS loader runs before the app-directories one -- so overrides keep working untouched, and
they apply to both packs exactly as an override does in menus. A project that wants to
override one version only puts its file at the pack path instead.

``pack_template`` therefore resolves the pack path alone. Trying the flat path first, the way
menus does, would find the forwarder and recurse.

Cards' own renders swap the name instead
----------------------------------------
The forwarders are for callers outside cards. Cards itself skips them: ``CardBase.render``
passes its template name through ``resolve_template``, and every include inside a pack
template (and in ``panel_layout.html``) is written

    {% pack_path 'cards/standard/_reload_button.html' as pack_include %}{% include pack_include %}

``resolve_template`` swaps ``cards/standard/`` for ``cards/<pack>/standard/`` when the file
Django finds at the flat path is cards' own forwarder, and leaves the name alone when it is a
project's override (or not a pack template at all), so overrides win exactly as before. It
saves a forwarder's second lookup and context copy per template -- around 20 microseconds
each with the cached loader, five of them in a plain card. Which file owns a flat name is
remembered per name, and forgotten when ``TEMPLATES`` changes -- except under ``DEBUG``,
where it is checked on every render, so an override added while the server runs shows at once.
"""
import os

from django.conf import settings
from django.core.signals import setting_changed
from django.dispatch import receiver
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.utils.module_loading import import_string

DEFAULT_PACK = 'bootstrap4'
PACKS = ('bootstrap4', 'bootstrap5')

# The Bootstrap naming that is not markup and so cannot live in a template folder: class
# strings built in Python, and the ones the shared treegrid script writes from JavaScript.
# Everything else a pack varies is in its templates.
PACK_CLASSES = {
    'bootstrap4': {
        # add_m2m_entry's default badge, and add_entry(badge=True).
        'm2m_badge': 'badge badge-pill badge-primary',
        'entry_badge': 'badge-secondary',
        # The float on CardList's list and details columns.
        'column_float': 'float-left',
        # Written by the shared treegrid script: the column filter selects, the count beside
        # a JS filter value, and the gap after a context menu item's icon.
        'treegrid_select': 'form-control form-control-sm',
        'treegrid_facet_badge': 'badge badge-secondary ml-1',
        'treegrid_menu_icon': 'mr-2',
    },
    'bootstrap5': {
        # text-bg- rather than the bare bg- form: on a light colour bg- alone leaves
        # Bootstrap 5's white text on a pale ground, and the longer prefix picks the
        # contrasting foreground to go with it.
        'm2m_badge': 'badge rounded-pill text-bg-primary',
        'entry_badge': 'text-bg-secondary',
        'column_float': 'float-start',
        'treegrid_select': 'form-select form-select-sm',
        'treegrid_facet_badge': 'badge text-bg-secondary ms-1',
        'treegrid_menu_icon': 'me-2',
    },
}


def template_pack(request=None):
    """The pack name for this request, from the setting."""
    configured = getattr(settings, 'DJANGO_CARDS_TEMPLATE_PACK', DEFAULT_PACK)
    if callable(configured):
        return configured(request)
    if '.' in configured:
        return import_string(configured)(request)
    return configured


def pack_class(name, request=None):
    """A Bootstrap class string spelled for this request's pack."""
    pack = template_pack(request)
    return PACK_CLASSES.get(pack, PACK_CLASSES[DEFAULT_PACK])[name]


def pack_classes(request=None):
    """Every class string for this request's pack, for handing to JavaScript in one go."""
    pack = template_pack(request)
    return PACK_CLASSES.get(pack, PACK_CLASSES[DEFAULT_PACK])


def pack_template(name, request=None):
    """The pack's copy of ``name``, which is a path below the pack folder.

    Pack-only on purpose: the flat path in front of it is either a project's override or the
    forwarder that calls this, and resolving it here would send the forwarder back to itself.
    """
    return get_template(f'cards/{template_pack(request)}/{name}')


def render_pack_template(name, context, request=None):
    return pack_template(name, request).render(context)


# Cards' own template folder, to tell its forwarders from a project's override at the same path.
_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
_FLAT_PREFIX = 'cards/standard/'


def _same_file(a, b):
    """Whether two paths name one file, however each is spelled (case, separators, links)."""
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


# Flat name -> whether what Django loads there is cards' own forwarder. It depends on the
# template folders, not the request, so it is worked out once per name; a change to TEMPLATES
# (an override_settings in a test, say) clears it, as it resets Django's own engines. Not
# kept under DEBUG, where an override added while the server runs must show on the next
# render, as it did when every render went through the forwarder.
_OWN_FORWARDER = {}


@receiver(setting_changed)
def _forget_forwarders(setting, **kwargs):
    if setting == 'TEMPLATES':
        _OWN_FORWARDER.clear()


def _is_own_forwarder(name):
    remember = not settings.DEBUG
    if remember and name in _OWN_FORWARDER:
        return _OWN_FORWARDER[name]
    rest = name[len('cards/'):]
    own_path = os.path.join(_TEMPLATES_DIR, 'cards', *rest.split('/'))
    has_pack_copy = os.path.exists(os.path.join(_TEMPLATES_DIR, 'cards', DEFAULT_PACK, *rest.split('/')))
    verdict = False
    if has_pack_copy:
        try:
            origin = get_template(name).origin.name
        except TemplateDoesNotExist:
            origin = None
        # An origin that is not a file (a locmem or database loader) is not ours.
        verdict = bool(origin) and os.path.isabs(origin) and _same_file(origin, own_path)
    if remember:
        _OWN_FORWARDER[name] = verdict
    return verdict


def resolve_template(name, request=None):
    """The template to render for ``name``: its pack copy, unless something else owns the name.

    A ``cards/standard/`` name whose file is cards' own forwarder becomes the request's pack
    path, so the card renders the pack's markup directly -- no forwarder is loaded, and no
    second render copies the context. A name a project overrides at the flat path, and any
    name that is not a pack template, comes back unchanged: the override wins on both packs,
    as it did when every render went through the forwarder.
    """
    if name.startswith(_FLAT_PREFIX) and _is_own_forwarder(name):
        return f'cards/{template_pack(request)}/{name[len("cards/"):]}'
    return name

