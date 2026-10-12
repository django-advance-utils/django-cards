from ajax_helpers.html_include import SourceBase


class DemoCSS(SourceBase):
    static_path = '/'
    css_filename = 'main.css'


class Bootstrap5(SourceBase):
    """Bootstrap 5, so the examples can be looked at on either version.

    ajax_helpers ships Bootstrap 4 (``ajax_helpers.includes.Bootstrap``, pinned at 4.6.0) and
    there is no Bootstrap 5 equivalent upstream yet, so the example app carries its own rather
    than wait for one. Served from our own static files, never a CDN: the files under
    ``cards_examples/static/cards_examples/bootstrap5/`` are bootstrap 5.3.3 copied unchanged
    from the npm package's ``dist/`` directory, and with no ``cdn_path`` SourceBase always uses
    ``static_path``.

    The bundle is deliberate: it carries Popper, which Bootstrap 5 needs for dropdowns and
    tooltips, and it must load *after* jQuery for Bootstrap's jQuery plugin interface to be
    registered. ``base.html`` keeps that order.
    """
    static_path = 'cards_examples/bootstrap5/'
    js_filename = 'bootstrap.bundle.min.js'
    css_filename = 'bootstrap.min.css'


packages = {
    'standard': [DemoCSS],
    'bootstrap5': [Bootstrap5],
}
