"""Every Bootstrap 4 name in the package carries its Bootstrap 5 twin, and vice versa.

django-cards renders for projects on Bootstrap 4 and projects on Bootstrap 5 out of one set
of templates, by emitting both spellings side by side: `class="mr-auto me-auto"`,
`data-toggle="collapse" data-bs-toggle="collapse"`. An unknown class or data attribute is
inert in either version, so each framework picks up the half it understands and ignores the
other.

That only holds while it is done everywhere. A single template that gains an `ml-2` and no
`ms-2` is a gap nobody sees under Bootstrap 4 -- and a single `ms-1` with no `ml-1` is a gap
nobody sees under Bootstrap 5, which is exactly how four of them reached
``default_body.html`` before this test existed. Both directions are checked here.

The convention the checks encode:

- a class token is followed by its twin inside the same quoted run, in either order;
- a Bootstrap data attribute is followed immediately by its ``data-bs-`` twin with the same
  value, so ``data-toggle="tab" data-bs-toggle="tab"``.

When something genuinely cannot carry both, it does not get an exemption here -- it stops
using either framework's name. The lightbox close button is the worked example: Bootstrap 4's
``.close`` styles a `&times;` the markup supplies while Bootstrap 5's ``.btn-close`` must be
empty and draws its own, so an element with both shows two crosses. It owns its appearance
through ``.django-card__modal-close`` instead.
"""
import os
import re

from django.test import SimpleTestCase

import cards

PACKAGE_ROOT = os.path.dirname(os.path.abspath(cards.__file__))

# Directories holding third-party code that is not ours to respell.
VENDORED = (os.path.join('static', 'cards', 'jstree'),)

# Bootstrap 4 token -> Bootstrap 5 token. Every pair is safe to carry together: the
# Bootstrap 5 name is either absent from Bootstrap 4 (inert there) or present with the
# same meaning (`w-100`, `rounded-pill`, `bg-*`).
CLASS_PAIRS = {
    'float-left': 'float-start',
    'float-right': 'float-end',
    'text-left': 'text-start',
    'text-right': 'text-end',
    'font-weight-bold': 'fw-bold',
    'dropdown-menu-right': 'dropdown-menu-end',
    'btn-block': 'w-100',
    'badge-primary': 'bg-primary',
    'badge-secondary': 'bg-secondary',
    'badge-pill': 'rounded-pill',
}
for _n in list('012345') + ['auto']:
    CLASS_PAIRS[f'ml-{_n}'] = f'ms-{_n}'
    CLASS_PAIRS[f'mr-{_n}'] = f'me-{_n}'
    CLASS_PAIRS[f'pl-{_n}'] = f'ps-{_n}'
    CLASS_PAIRS[f'pr-{_n}'] = f'pe-{_n}'

# The reverse check runs only over Bootstrap 5 names that do not exist in Bootstrap 4, so a
# bare one is unambiguously a gap. `w-100`, `rounded-pill` and `bg-primary` are left out:
# all three are ordinary Bootstrap 4 utilities and stand on their own perfectly well.
BS5_ONLY = {bs5: bs4 for bs4, bs5 in CLASS_PAIRS.items()
            if bs5 not in ('w-100', 'rounded-pill', 'bg-primary', 'bg-secondary')}
BS5_ONLY['form-select'] = 'form-control'
BS5_ONLY['form-select-sm'] = 'form-control-sm'

# Bootstrap's own data attributes, which became `data-bs-*` in Bootstrap 5.
DATA_ATTRS = ('toggle', 'target', 'dismiss', 'parent', 'content', 'trigger')

# `data-target` on `.panel-collapse-btn` is the panel layout's own attribute, read by
# panel_layout.js:352. It was never Bootstrap's and must not grow a `data-bs-` twin, or
# Bootstrap 5 would try to drive a collapse that does not exist.
NOT_BOOTSTRAP = re.compile(r'data-target="panel_region_')

# A selector matching both spellings, e.g. `[data-toggle="tooltip"],[data-bs-toggle=...]`
# in groups.html. That is a jQuery selector, not markup, so the "twin follows immediately"
# rule does not apply to it.
SELECTOR = re.compile(r'\[data-(?:bs-)?[a-z]+="[^"]*"\]')


def _source_files():
    for dirpath, _dirnames, filenames in os.walk(PACKAGE_ROOT):
        rel_dir = os.path.relpath(dirpath, PACKAGE_ROOT)
        if any(rel_dir.startswith(v) for v in VENDORED):
            continue
        for name in filenames:
            if name.endswith(('.html', '.py', '.js')):
                path = os.path.join(dirpath, name)
                yield os.path.relpath(path, PACKAGE_ROOT), open(path).read()


def _quoted_run(text, index):
    """The quoted string the character at `index` sits inside.

    Good enough to stand in for "the same class attribute" in a template and "the same
    string literal" in Python or JavaScript, which is the granularity the twin has to
    share. Falls back to the whole line when the token is not quoted at all.
    """
    line_start = text.rfind('\n', 0, index) + 1
    line_end = text.find('\n', index)
    if line_end == -1:
        line_end = len(text)
    best = (line_start, line_end)
    for quote in ('"', "'"):
        start = text.rfind(quote, line_start, index)
        if start == -1:
            continue
        end = text.find(quote, index)
        if end == -1 or end > line_end:
            continue
        if start > best[0]:
            best = (start, end)
    return text[best[0]:best[1]]


def _line_of(text, index):
    return text.count('\n', 0, index) + 1


class TestBootstrapClassesAreDualled(SimpleTestCase):

    def _scan(self, pairs):
        missing = []
        for rel_path, text in _source_files():
            for token, twin in pairs.items():
                for match in re.finditer(rf'(?<![\w-]){re.escape(token)}(?![\w-])', text):
                    run = _quoted_run(text, match.start())
                    if re.search(rf'(?<![\w-]){re.escape(twin)}(?![\w-])', run):
                        continue
                    missing.append(
                        f'{rel_path}:{_line_of(text, match.start())}: '
                        f'{token!r} without {twin!r}'
                    )
        return missing

    def test_every_bootstrap4_class_carries_its_bootstrap5_twin(self):
        missing = self._scan(CLASS_PAIRS)
        self.assertEqual(missing, [], 'Bootstrap 5 name missing beside a Bootstrap 4 one:\n'
                                      + '\n'.join(missing))

    def test_every_bootstrap5_only_class_carries_its_bootstrap4_twin(self):
        """The direction that fails silently on a Bootstrap 4 page."""
        missing = self._scan(BS5_ONLY)
        self.assertEqual(missing, [], 'Bootstrap 4 name missing beside a Bootstrap 5 one:\n'
                                      + '\n'.join(missing))


class TestBootstrapDataAttributesAreDualled(SimpleTestCase):

    def test_every_bootstrap_data_attribute_carries_its_data_bs_twin(self):
        missing = []
        for rel_path, text in _source_files():
            for attr in DATA_ATTRS:
                pattern = rf'(?<![\w-])data-{attr}=("[^"]*")'
                for match in re.finditer(pattern, text):
                    if NOT_BOOTSTRAP.match(match.group(0)):
                        continue
                    if SELECTOR.match(text, max(0, match.start() - 1)):
                        continue
                    twin = f' data-bs-{attr}={match.group(1)}'
                    if text[match.end():match.end() + len(twin)] == twin:
                        continue
                    missing.append(
                        f'{rel_path}:{_line_of(text, match.start())}: '
                        f'data-{attr} without data-bs-{attr} directly after it'
                    )
        self.assertEqual(missing, [], 'Bootstrap 5 data attribute missing:\n'
                                      + '\n'.join(missing))

    def test_no_data_bs_attribute_stands_alone(self):
        """The direction that fails silently on a Bootstrap 4 page."""
        missing = []
        for rel_path, text in _source_files():
            for attr in DATA_ATTRS:
                for match in re.finditer(rf'(?<![\w-])data-bs-{attr}=("[^"]*")', text):
                    if SELECTOR.match(text, max(0, match.start() - 1)):
                        continue
                    twin = f'data-{attr}={match.group(1)} '
                    if text[max(0, match.start() - len(twin)):match.start()] == twin:
                        continue
                    missing.append(
                        f'{rel_path}:{_line_of(text, match.start())}: '
                        f'data-bs-{attr} without data-{attr} directly before it'
                    )
        self.assertEqual(missing, [], 'Bootstrap 4 data attribute missing:\n'
                                      + '\n'.join(missing))


class TestNoFrameworkOwnedCloseButton(SimpleTestCase):
    """`.close` and `.btn-close` are the pair that cannot be carried together."""

    def test_close_classes_are_not_used(self):
        found = []
        for rel_path, text in _source_files():
            for match in re.finditer(r'class="([^"]*)"', text):
                classes = match.group(1).split()
                if 'close' in classes or 'btn-close' in classes:
                    found.append(f'{rel_path}:{_line_of(text, match.start())}')
        self.assertEqual(found, [],
                         'Use .django-card__modal-close instead -- Bootstrap 4 .close and '
                         'Bootstrap 5 .btn-close cannot both be carried:\n' + '\n'.join(found))
