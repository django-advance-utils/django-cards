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
"""
from django.conf import settings
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
