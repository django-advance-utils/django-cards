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


packages = {
    # CardTree selection UI — jsTree requires jQuery.
    'jstree_default': [JSSourceTree, JSSourceDefaultTheme],
    'jstree_proton': [JSSourceTree, JSSourceDarkProtonTheme],
    'jstree_dark': [JSSourceTree, JSSourceDarkTheme],
    # Treegrid cards — FancyTree requires jQuery.
    'fancytree': [FancytreeJS, FancytreeAwesomeSkinCSS],
}
