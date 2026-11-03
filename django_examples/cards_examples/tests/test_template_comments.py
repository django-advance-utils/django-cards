"""A ``{# #}`` comment has to end on the line it starts on.

Django only reads ``{# ... #}`` as a comment when both ends are on one line. One that runs on
to a second line is not a comment at all: the engine prints it, prose and all, into the page.
A note longer than a line goes in ``{% comment %} ... {% endcomment %}``.
"""
import pathlib
import re

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

import cards
from cards_examples.views.treegrid import TreegridBasicExample

TEMPLATE_DIRS = (
    pathlib.Path(cards.__file__).resolve().parent / 'templates',          # the package's own
    pathlib.Path(__file__).resolve().parents[1] / 'templates',          # the example app's
)
# A {# with no #} after it on the same line.
OPEN_COMMENT = re.compile(r'\{#(?!.*#\}).*$')


class TestTemplateCommentsEndOnTheirLine(TestCase):

    def test_no_template_opens_a_comment_it_does_not_close_on_the_same_line(self):
        for directory in TEMPLATE_DIRS:
            templates = sorted(directory.rglob('*.html'))
            self.assertTrue(templates, directory)
            for path in templates:
                for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                    with self.subTest(template=path.relative_to(directory).as_posix(), line=number):
                        self.assertIsNone(OPEN_COMMENT.search(line), line.strip())

    def test_the_base_page_note_stays_out_of_the_page(self):
        """It used to be printed, braces and all, above the example app's menu bar."""
        request = RequestFactory().get('/treegrid/')
        request.user = get_user_model()(username='test', is_superuser=False)
        response = TreegridBasicExample.as_view()(request)
        response.render()
        self.assertNotIn("The example app's own chrome", response.content.decode())
