from ajax_helpers.html_include import SourceBase


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
    cdn_path = 'cdn.jsdelivr.net/npm/jquery.fancytree@2.38.5/dist/'
    cdn_js_path = ''
    js_filename = 'jquery.fancytree-all-deps.min.js'


class FancytreeAwesomeSkinCSS(SourceBase):
    cdn_path = 'cdn.jsdelivr.net/npm/jquery.fancytree@2.38.5/dist/'
    cdn_css_path = ''
    css_filename = 'skin-awesome/ui.fancytree.min.css'


packages = {
    'jstree_default': [JSSourceTree, JSSourceDefaultTheme],
    'jstree_proton': [JSSourceTree, JSSourceDarkProtonTheme],
    'jstree_dark': [JSSourceTree, JSSourceDarkTheme],
    'fancytree': [FancytreeJS, FancytreeAwesomeSkinCSS],
}
