from ajax_helpers.html_include import SourceBase


class DemoCSS(SourceBase):
    static_path = '/'
    css_filename = 'main.css'


packages = {
    'standard': [DemoCSS],
}
