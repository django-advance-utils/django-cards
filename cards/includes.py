from ajax_helpers.html_include import SourceBase, pip_version

# Stamped on local includes as ?v= so a new release busts browser caches.
version = pip_version('django-cards')


class JSSourceTree(SourceBase):
    static_path = 'cards/jstree/'
    js_filename = 'jstree.min.js'


class JSSourceDefaultTheme(SourceBase):
    static_path = 'cards/jstree/'
    css_filename = 'themes/default/style.css'


class JSSourceDarkTheme(SourceBase):
    static_path = 'cards/jstree/'
    css_filename = 'themes/default-dark/style.css'


class JSSourceDarkProtonTheme(SourceBase):
    static_path = 'cards/jstree/'
    css_filename = 'themes/proton/style.css'


class FancytreeJS(SourceBase):
    # FancyTree is a jQuery plugin. Treegrid cards still require jQuery until
    # migrated to a zero-dependency successor (e.g. Wunderbaum).
    #
    # Served from our own static files, never a CDN: with no cdn_path, SourceBase
    # always uses static_path whatever cdn= is passed. The files under
    # cards/static/cards/fancytree/ are jquery.fancytree 2.38.5 copied unchanged
    # from the npm package's dist/ directory, keeping its layout.
    static_path = 'cards/fancytree/'
    js_path = ''
    js_filename = 'jquery.fancytree-all-deps.min.js'


class FancytreeAwesomeSkinCSS(SourceBase):
    # Local only, as FancytreeJS. The skin's CSS refers to
    # ../skin-awesome/vline*.gif, which sit beside it in the same npm layout.
    static_path = 'cards/fancytree/'
    css_path = ''
    css_filename = 'skin-awesome/ui.fancytree.min.css'



class PanelLayoutSource(SourceBase):
    # The panel layout's own script and css (cards/standard/panel_layout.html). Taken
    # through lib_include so they carry ?v= like every other include: static is served
    # with a far-future expiry, and a browser that had the old panel_layout.js kept it.
    static_path = 'cards/panel_layout/'
    filename = 'panel_layout'


class PanelLinkedTablesJS(SourceBase):
    # Clicking a row in one panel's table to drive another; only a layout with linked
    # tables takes it.
    static_path = 'cards/panel_layout/'
    js_filename = 'panel_linked_tables.js'


packages = {
    # CardTree selection UI — jsTree requires jQuery.
    'jstree_default': [JSSourceTree, JSSourceDefaultTheme],
    'jstree_proton': [JSSourceTree, JSSourceDarkProtonTheme],
    'jstree_dark': [JSSourceTree, JSSourceDarkTheme],
    # Treegrid cards — FancyTree requires jQuery.
    'fancytree': [FancytreeJS, FancytreeAwesomeSkinCSS],
    # Panel layouts (cards/standard/panel_layout.html).
    'panel_layout': [PanelLayoutSource],
    'panel_linked_tables': [PanelLinkedTablesJS],
}
