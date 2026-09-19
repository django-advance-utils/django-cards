"""The two Bootstrap packs stay in step, and each renders its own version's names.

django-cards ships one template folder per Bootstrap version. That buys clean markup and room
for the versions to diverge structurally, at the cost dual emission did not have: a fix applied
to one pack and not the other is **silent**. Nothing in the rendered page looks wrong on the
version you happen to be looking at, and there is no twin missing from a class attribute for a
scanner to notice.

So the drift is what is pinned here. ``test_packs_are_identical_once_renamed`` normalises every
Bootstrap 4 name in a pack4 template to its Bootstrap 5 spelling and requires the result to
equal the pack5 template exactly. A caret fixed in one pack and not the other fails it, naming
the file. When the packs are *meant* to diverge -- a structural difference dual emission could
not have expressed, which is the reason for having packs at all -- the pair is added to
STRUCTURAL_DIVERGENCE with a note, and that is the moment someone has to think about it.

The rest of the file guards the parts of cards that a template folder cannot reach: the flat
forwarders that keep ``cards/standard/*.html`` working as the name projects use, the class
strings built in Python, and the ones the shared treegrid script writes from JavaScript.
"""
import json
import os
import re
import shutil
import tempfile

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.utils.safestring import mark_safe

import cards
from cards.card_list.base import CardListBaseMixin
from cards.panel_layout import PanelLayout
from cards.packs import DEFAULT_PACK, PACK_CLASSES, pack_class, template_pack

TEMPLATE_ROOT = os.path.join(os.path.dirname(os.path.abspath(cards.__file__)), 'templates', 'cards')
PACKS = ('bootstrap4', 'bootstrap5')

# Bootstrap 4 token -> Bootstrap 5 token, applied to normalise a pack4 template before
# comparing it with its pack5 twin. Only renames belong here.
RENAMES = {
    'float-left': 'float-start', 'float-right': 'float-end',
    'text-left': 'text-start', 'text-right': 'text-end',
    'dropdown-menu-right': 'dropdown-menu-end',
    'btn-block': 'w-100',
    'badge-pill': 'rounded-pill',
    'font-italic': 'fst-italic', 'text-monospace': 'font-monospace',
    'sr-only': 'visually-hidden', 'sr-only-focusable': 'visually-hidden-focusable',
    'custom-select': 'form-select', 'custom-select-sm': 'form-select-sm',
}
# The badge colours. text-bg- rather than the bare bg- the dual spelling used: on a light
# colour, bg- alone leaves Bootstrap 5's own foreground on a pale ground, and the longer
# prefix picks the contrasting one to go with it.
for _c in ('primary', 'secondary', 'success', 'danger', 'warning', 'info', 'light', 'dark'):
    RENAMES[f'badge-{_c}'] = f'text-bg-{_c}'
for _w in ('bold', 'bolder', 'normal', 'light', 'lighter'):
    RENAMES[f'font-weight-{_w}'] = f'fw-{_w}'
_SIZES = [str(n) for n in range(6)] + ['auto'] + [f'n{n}' for n in range(1, 6)]
for _bp in ('', 'sm-', 'md-', 'lg-', 'xl-'):
    for _n in _SIZES:
        RENAMES[f'ml-{_bp}{_n}'] = f'ms-{_bp}{_n}'
        RENAMES[f'mr-{_bp}{_n}'] = f'me-{_bp}{_n}'
        if not _n.startswith('n'):  # padding has no negative scale
            RENAMES[f'pl-{_bp}{_n}'] = f'ps-{_bp}{_n}'
            RENAMES[f'pr-{_bp}{_n}'] = f'pe-{_bp}{_n}'
for _bp in ('sm-', 'md-', 'lg-', 'xl-'):
    RENAMES[f'float-{_bp}left'] = f'float-{_bp}start'
    RENAMES[f'float-{_bp}right'] = f'float-{_bp}end'
    RENAMES[f'text-{_bp}left'] = f'text-{_bp}start'
    RENAMES[f'text-{_bp}right'] = f'text-{_bp}end'

# A <select> is styled by .form-control in Bootstrap 4 and .form-select in Bootstrap 5. Scoped
# to the element rather than listed above, because .form-control is Bootstrap 5's own name for
# every other kind of input and a blanket rename would respell those too.
SELECT_RENAMES = {'form-control': 'form-select', 'form-control-sm': 'form-select-sm'}
SELECT_TAG = re.compile(r'<select\b[^>]*>', re.S)

# Bootstrap's own data attributes, which became data-bs-* in Bootstrap 5. The whole plugin
# option surface, not just what the packs use today -- the point is the one added next.
DATA_ATTRS = (
    'toggle', 'target', 'dismiss', 'parent', 'content', 'trigger', 'placement', 'html',
    'offset', 'backdrop', 'keyboard', 'focus', 'ride', 'slide', 'slide-to', 'interval',
    'pause', 'wrap', 'container', 'delay', 'animation', 'boundary', 'display', 'reference',
    'spy', 'method', 'autohide',
)
# `data-target` on `.panel-collapse-btn` is the panel layout's own attribute, read by
# panel_layout.js. It was never Bootstrap's, so Bootstrap 5 did not rename it.
NOT_BOOTSTRAP = re.compile(r'data-target="panel_region_')

# Templates whose two packs differ by more than a rename, each with why.
STRUCTURAL_DIVERGENCE = {
    'standard/_lightbox_close.html':
        'Bootstrap 4 styles .close around a times the markup supplies; Bootstrap 5 styles '
        '.btn-close, which must be empty and draws its own. The element itself differs, which '
        'is the kind of difference dual emission could not express at all -- it is why the '
        'close button is a template of its own rather than two class names on one button.',
}

# Templates that stay outside the packs, and why. Everything else under cards/templates/cards/
# that is not a pack folder must be a forwarder.
FLAT_TEMPLATES = {
    'groups/groups.html': 'card group wrapper; its only Bootstrap names are in a jQuery '
                          'selector that deliberately matches both spellings, because it runs '
                          'over the whole page and not just over cards',
    'standard/blank.html': 'empty',
    'standard/panel_layout.html': 'the panel layout container; its classes are the panel '
                                  'layout\'s own, not Bootstrap\'s',
    'standard/_card_css.html': 'a stylesheet link',
    'standard/_cards_on_ready.html': 'script',
    'standard/_column_search_script.html': 'script',
    'standard/_export_script.html': 'script',
    'standard/_reload_script.html': 'script',
    'standard/_search_script.html': 'script',
    'standard/_treegrid_css.html': 'stylesheet',
    'standard/_treegrid_init.html': 'a card\'s treegrid config, which carries the pack\'s '
                                    'class names rather than naming a version itself',
    'standard/_treegrid_script.html': 'the shared treegrid behaviour, rendered once per '
                                      'process and so unable to name a version; it reads the '
                                      'class names out of each card\'s config',
    'standard/_treegrid_shared.html': 'two includes',
}


def _normalise(text):
    """Rewrite a Bootstrap 4 template into how the Bootstrap 5 one should read."""
    def respell_select(match):
        tag = match.group(0)
        for bs4, bs5 in sorted(SELECT_RENAMES.items(), key=lambda kv: -len(kv[0])):
            tag = re.sub(rf'(?<![\w-]){re.escape(bs4)}(?![\w-])', bs5, tag)
        return tag
    text = SELECT_TAG.sub(respell_select, text)
    for bs4, bs5 in sorted(RENAMES.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(rf'(?<![\w-]){re.escape(bs4)}(?![\w-])', bs5, text)
    for attr in DATA_ATTRS:
        def respell(match, attr=attr):
            if NOT_BOOTSTRAP.match(match.group(0)):
                return match.group(0)
            return f'data-bs-{attr}=' + match.group(1)
        text = re.sub(rf'(?<![\w-])data-{attr}=("[^"]*"|\'[^\']*\')', respell, text)
    return text


def _pack_files(pack):
    root = os.path.join(TEMPLATE_ROOT, pack)
    found = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name.endswith('.html'):
                found.append(os.path.relpath(os.path.join(dirpath, name), root))
    return sorted(found)


def _flat_files():
    found = []
    for dirpath, dirnames, filenames in os.walk(TEMPLATE_ROOT):
        dirnames[:] = [d for d in dirnames if d not in PACKS]
        for name in filenames:
            if name.endswith('.html'):
                found.append(os.path.relpath(os.path.join(dirpath, name), TEMPLATE_ROOT))
    return sorted(found)


def _read(*parts):
    with open(os.path.join(TEMPLATE_ROOT, *parts)) as f:
        return f.read()


class TestPacksStayInStep(SimpleTestCase):

    def test_packs_hold_the_same_templates(self):
        self.assertEqual(_pack_files('bootstrap4'), _pack_files('bootstrap5'),
                         'A template was added to one pack and not the other')

    def test_packs_are_identical_once_renamed(self):
        """The check that catches a fix applied to one pack only."""
        drifted = []
        for name in _pack_files('bootstrap4'):
            if name in STRUCTURAL_DIVERGENCE:
                continue
            if _normalise(_read('bootstrap4', name)) != _read('bootstrap5', name):
                drifted.append(name)
        self.assertEqual(drifted, [],
                         'These differ by more than a Bootstrap rename. Either the two packs '
                         'have drifted, or the difference is deliberate and belongs in '
                         'STRUCTURAL_DIVERGENCE with a note:\n' + '\n'.join(drifted))

    def test_no_bootstrap4_names_left_in_the_bootstrap5_pack(self):
        """A pack5 template that kept a Bootstrap 4 spelling renders nothing on 5."""
        found = []
        for name in _pack_files('bootstrap5'):
            text = _read('bootstrap5', name)
            for bs4 in RENAMES:
                if re.search(rf'(?<![\w-]){re.escape(bs4)}(?![\w-])', text):
                    found.append(f'bootstrap5/{name}: {bs4!r}')
            for attr in DATA_ATTRS:
                for match in re.finditer(rf'(?<![\w-])data-{attr}="[^"]*"', text):
                    if not NOT_BOOTSTRAP.match(match.group(0)):
                        found.append(f'bootstrap5/{name}: data-{attr}')
        self.assertEqual(found, [], 'Bootstrap 4 names in the Bootstrap 5 pack:\n' + '\n'.join(found))

    def test_no_bootstrap5_select_styling_in_the_bootstrap4_pack(self):
        """.form-select is the one Bootstrap 5 name that is not in RENAMES' keys' range."""
        found = [f'bootstrap4/{name}' for name in _pack_files('bootstrap4')
                 if re.search(r'(?<![\w-])form-select(?![\w-])', _read('bootstrap4', name))]
        self.assertEqual(found, [], '\n'.join(found))


class TestFlatPathsStillResolve(SimpleTestCase):
    """cards/standard/*.html stays the name projects use; behind it sits the pack.

    Unlike django-menus, cards cannot simply stop shipping the flat paths: projects reference
    them from a CardBase.templates subclass, from {% include %} lines in their own copies of a
    card template, and as the path they override. So every pack template keeps a file there
    holding one {% pack_source %} tag.
    """

    def test_every_pack_template_has_a_forwarder(self):
        missing = [name for name in _pack_files('bootstrap4')
                   if not os.path.exists(os.path.join(TEMPLATE_ROOT, name))]
        self.assertEqual(missing, [], 'A pack template with nothing at its flat path is '
                                      'unreachable by the name projects use:\n' + '\n'.join(missing))

    def test_a_forwarder_holds_nothing_but_its_own_tag(self):
        """Markup in a forwarder would be markup outside any pack, shown on both versions."""
        wrong = []
        for name in _pack_files('bootstrap4'):
            expected = "{% load django_cards_tags %}{% pack_source '" + name + "' %}\n"
            if _read(name) != expected:
                wrong.append(name)
        self.assertEqual(wrong, [], 'Not a plain forwarder to its own pack template:\n' + '\n'.join(wrong))

    def test_every_flat_template_is_a_forwarder_or_listed(self):
        """A new template must land in the packs, or say here why it does not need to."""
        packed = set(_pack_files('bootstrap4'))
        stray = [name for name in _flat_files() if name not in packed and name not in FLAT_TEMPLATES]
        self.assertEqual(stray, [], 'Outside the packs and not in FLAT_TEMPLATES:\n' + '\n'.join(stray))

    def test_the_templates_that_stay_flat_name_no_bootstrap_version(self):
        """Whatever sits outside the packs is served to both, so it cannot pick a side."""
        found = []
        for name in FLAT_TEMPLATES:
            if name in ('groups/groups.html', 'standard/_treegrid_script.html'):
                continue  # both deliberately carry both spellings; checked below
            text = _read(name)
            for token in list(RENAMES) + list(RENAMES.values()):
                if token in ('w-100', 'rounded-pill'):
                    continue  # ordinary Bootstrap 4 utilities as well
                if re.search(rf'(?<![\w-]){re.escape(token)}(?![\w-])', text):
                    found.append(f'{name}: {token!r}')
        self.assertEqual(found, [], 'A version-specific Bootstrap name outside the packs:\n'
                         + '\n'.join(found))


class TestSharedTreegridScript(SimpleTestCase):
    """The shared treegrid half is rendered once per process, so it cannot name a version.

    It is ~110 KiB emitted once per page and cached for the life of the process, which is why
    it is not a pack template: the first request served would freeze its Bootstrap version for
    every request after it. The few class names it writes come down in each card's config.
    """

    def _script(self):
        return _read('standard/_treegrid_script.html')

    def test_it_names_no_bootstrap5_class(self):
        found = [bs5 for bs5 in RENAMES.values()
                 if bs5 not in ('w-100', 'rounded-pill')
                 and re.search(rf'(?<![\w-]){re.escape(bs5)}(?![\w-])', self._script())]
        self.assertEqual(found, [], f'Bootstrap 5 names frozen into the shared script: {found}')

    def test_its_fallbacks_are_the_default_pack(self):
        """The `||` defaults stand in for a card whose config predates the packs."""
        script = self._script()
        for key in ('treegrid_select', 'treegrid_facet_badge', 'treegrid_menu_icon'):
            match = re.search(rf"PACK_CLASSES\.{key} \|\| '([^']*)'", script)
            self.assertIsNotNone(match, f'no fallback found for {key}')
            self.assertEqual(match.group(1), PACK_CLASSES[DEFAULT_PACK][key],
                             f'the {key} fallback has drifted from the default pack')

    def test_a_card_hands_its_pack_down(self):
        for pack in PACKS:
            with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                html = render_to_string('cards/standard/_treegrid_init.html', {'card': _Card()})
                self.assertIn(f"pack: '{pack}'", html)
                config = re.search(r'pack_classes: (\{.*?\})\n', html, re.S).group(1)
                self.assertEqual(json.loads(config), PACK_CLASSES[pack])


class _Rendered:
    def __init__(self, html=''):
        self.html = html

    @property
    def render(self):
        return mark_safe(self.html)

    def __bool__(self):
        return bool(self.html)


class _Card:
    """Enough of a card for the templates under test to render."""
    code = 'probe'
    header_icon = None
    header_css_class = ''
    enable_collapse = True
    collapsed = False
    searchable = True
    exportable = True
    ajax_reload = True
    extra_card_info = {}
    child_card_groups = []
    panels = []
    rows = []
    entries = []
    datatable = None
    column_search = False
    title = 'Probe card'

    def __init__(self):
        self.menu = _Rendered('')
        self.tab_menu = _Rendered('')


def _render(template, pack, context=None):
    with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
        return render_to_string(f'cards/{template}',
                                {'card': _Card(), 'show_header': True, **(context or {})})


class TestPackSelection(SimpleTestCase):
    """The setting actually reaches the markup, through the forwarders and from Python."""

    def test_a_class_follows_the_pack(self):
        self.assertIn('ml-2', _render('standard/_reload_button.html', 'bootstrap4'))
        self.assertNotIn('ms-2', _render('standard/_reload_button.html', 'bootstrap4'))
        self.assertIn('ms-2', _render('standard/_reload_button.html', 'bootstrap5'))
        self.assertNotIn('ml-2', _render('standard/_reload_button.html', 'bootstrap5'))

    def test_a_data_attribute_follows_the_pack(self):
        bs4 = _render('standard/_export_button.html', 'bootstrap4')
        bs5 = _render('standard/_export_button.html', 'bootstrap5')
        self.assertIn('data-toggle="dropdown"', bs4)
        self.assertNotIn('data-bs-toggle', bs4)
        self.assertIn('data-bs-toggle="dropdown"', bs5)
        self.assertNotIn('data-toggle="dropdown"', bs5)

    def test_a_whole_card_is_single_version(self):
        """End to end, through the forwarder and the includes it pulls in."""
        for pack, wanted, unwanted in (('bootstrap4', 'mr-auto', 'me-auto'),
                                       ('bootstrap5', 'me-auto', 'mr-auto')):
            html = _render('standard/default.html', pack)
            self.assertIn(wanted, html)
            self.assertNotIn(unwanted, html)

    def test_the_badge_built_in_python_follows_the_pack(self):
        with override_settings(DJANGO_CARDS_TEMPLATE_PACK='bootstrap4'):
            self.assertEqual(pack_class('entry_badge'), 'badge-secondary')
            self.assertIn('badge-pill', pack_class('m2m_badge'))
        with override_settings(DJANGO_CARDS_TEMPLATE_PACK='bootstrap5'):
            self.assertEqual(pack_class('entry_badge'), 'text-bg-secondary')
            self.assertIn('rounded-pill', pack_class('m2m_badge'))
            self.assertNotIn('badge-pill', pack_class('m2m_badge'))

    def test_the_card_list_columns_follow_the_pack(self):
        """list_class and details_class are properties for this reason: Bootstrap 5 renamed
        the float utility, and a class attribute could only have named one version."""
        class _View(CardListBaseMixin):
            request = None

        view = _View()
        with override_settings(DJANGO_CARDS_TEMPLATE_PACK='bootstrap4'):
            self.assertTrue(view.list_class.endswith('float-left'), view.list_class)
            self.assertTrue(view.details_class.endswith('float-left'), view.details_class)
        with override_settings(DJANGO_CARDS_TEMPLATE_PACK='bootstrap5'):
            self.assertTrue(view.list_class.endswith('float-start'), view.list_class)
            self.assertTrue(view.details_class.endswith('float-start'), view.details_class)

    def test_a_subclass_can_still_replace_the_column_classes(self):
        class _View(CardListBaseMixin):
            list_class = 'col-12'

        self.assertEqual(_View().list_class, 'col-12')

    def test_assigning_the_column_classes_still_works(self):
        """as_view(list_class=...) assigns on the instance, which a bare property refuses."""
        view = CardListBaseMixin()
        view.list_class = 'col-4'
        view.details_class = 'col-8'
        self.assertEqual((view.list_class, view.details_class), ('col-4', 'col-8'))

    def test_default_is_bootstrap4(self):
        with override_settings():
            from django.conf import settings
            if hasattr(settings, 'DJANGO_CARDS_TEMPLATE_PACK'):
                del settings.DJANGO_CARDS_TEMPLATE_PACK
            self.assertEqual(template_pack(), 'bootstrap4')

    def test_the_setting_may_be_a_callable_taking_the_request(self):
        """How the example app serves both versions off one deployment."""
        with override_settings(DJANGO_CARDS_TEMPLATE_PACK=lambda request: 'bootstrap5'):
            self.assertEqual(template_pack(None), 'bootstrap5')
        with override_settings(
                DJANGO_CARDS_TEMPLATE_PACK='cards_examples.tests.test_template_packs.pack_five'):
            self.assertEqual(template_pack(None), 'bootstrap5')


def pack_five(_request):
    """Target for the dotted-path form of the setting, exercised above."""
    return 'bootstrap5'


class TestPanelSplitThroughTheForwarder(SimpleTestCase):
    """The panel layout is the awkward path: a flat template includes a pack one, which
    includes itself.

    cards/standard/panel_layout.html stays outside the packs and reaches _panel_split.html
    through its forwarder with {% include ... with split=root %}, and the split includes
    itself the same way for a nested one. So this covers three things at once: variables
    pushed by {% include ... with %} surviving the forwarder's context, the recursion, and
    the request that panel_layout.py puts in the context arriving where the pack is chosen.
    """

    TAB = {'name': 'one', 'title': 'One', 'active': True}
    NESTED = {'type': 'region', 'name': 'inner', 'collapsible': True, 'cards': []}

    def _split(self):
        return {'direction': 'horizontal', 'resizable': True, 'children': [
            {'type': 'region', 'name': 'main', 'collapsible': True, 'cards': [], 'tabs': [self.TAB]},
            {'type': 'split', 'split': {'direction': 'vertical', 'resizable': False,
                                        'children': [self.NESTED]}},
        ]}

    def _render(self, pack):
        with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
            return render_to_string('cards/standard/panel_layout.html',
                                    {'layout_id': 'probe', 'root': self._split(), 'persist': False})

    def test_the_tab_link_follows_the_pack(self):
        bs4, bs5 = self._render('bootstrap4'), self._render('bootstrap5')
        self.assertIn('data-toggle="tab"', bs4)
        self.assertNotIn('data-bs-toggle="tab"', bs4)
        self.assertIn('data-bs-toggle="tab"', bs5)
        self.assertNotIn('data-toggle="tab"', bs5)

    def test_the_nested_split_renders_through_the_forwarder_too(self):
        for pack in PACKS:
            self.assertIn('id="panel_region_inner"', self._render(pack))

    def test_the_panel_layouts_own_data_target_is_not_respelled(self):
        """It looks like Bootstrap's and is not: panel_layout.js reads it."""
        bs5 = self._render('bootstrap5')
        self.assertIn('data-target="panel_region_main"', bs5)
        self.assertNotIn('data-bs-target="panel_region_main"', bs5)

    def test_the_layout_puts_the_request_in_its_context(self):
        """Without this entry the split below resolves the pack with no request at all."""
        class _View:
            request = 'the-request'

        self.assertEqual(PanelLayout(view=_View()).get_render_html_context()['request'],
                         'the-request')

    def test_the_request_decides_the_pack_not_the_default(self):
        """What panel_layout.py's context entry buys: the split follows the request."""
        factory = RequestFactory()
        with override_settings(DJANGO_CARDS_TEMPLATE_PACK=lambda request: (
                'bootstrap5' if request is not None else 'bootstrap4')):
            html = render_to_string('cards/standard/panel_layout.html',
                                    {'layout_id': 'probe', 'root': self._split(),
                                     'persist': False, 'request': factory.get('/')})
            self.assertIn('data-bs-toggle="tab"', html)


class TestProjectOverrideStillWins(SimpleTestCase):
    """A project's own file at the flat path shadows the forwarder, as it always did.

    The DIRS loader runs ahead of the app-directories one, so the override is found first and
    the pack behind the forwarder is never reached. That is the whole reason the flat paths
    are kept: an override written before the packs existed goes on working, on both versions.
    """

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        path = os.path.join(self.dir, 'cards', 'standard')
        os.makedirs(path)
        with open(os.path.join(path, '_reload_button.html'), 'w') as f:
            f.write('<button class="project-reload">reload</button>')

    def _templates_setting(self):
        from django.conf import settings
        engine = dict(settings.TEMPLATES[0])
        engine['DIRS'] = [self.dir]
        return [engine]

    def test_an_override_at_the_flat_path_wins_on_both_packs(self):
        with override_settings(TEMPLATES=self._templates_setting()):
            for pack in PACKS:
                with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
                    html = render_to_string('cards/standard/_reload_button.html', {'card': _Card()})
                    self.assertIn('project-reload', html)


class TestLightboxCloseButton(SimpleTestCase):
    """The pair that dual emission could not carry, and packs can.

    An element with both .close and .btn-close shows two crosses under Bootstrap 5, so the
    dual-spelled templates had to invent a third class and style it themselves. Each pack now
    uses its framework's own.
    """

    def test_bootstrap4_supplies_the_cross_itself(self):
        markup = _read('bootstrap4', 'standard/_lightbox_close.html')
        self.assertIn('class="close"', markup)
        self.assertIn('&times;', markup)

    def test_bootstrap5_leaves_the_button_empty(self):
        markup = _read('bootstrap5', 'standard/_lightbox_close.html')
        self.assertIn('class="btn-close"', markup)
        self.assertNotIn('&times;', markup)

    def test_neither_pack_styles_a_close_button_of_its_own(self):
        found = [f'{pack}/{name}' for pack in PACKS for name in _pack_files(pack)
                 if 'django-card__modal-close' in _read(pack, name)]
        self.assertEqual(found, [], 'The invented class the dual spelling needed is back:\n'
                         + '\n'.join(found))
