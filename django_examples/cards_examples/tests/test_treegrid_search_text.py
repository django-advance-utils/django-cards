"""A treegrid searches, filters and labels by the text it shows, not by the markup behind it.

A node's title, and a cell in an 'html' column, is drawn as markup, so text bound for one is
escaped first and arrives as "Nuts &amp; Bolts". The grid used to compare what was typed with
that escaped string -- fancytree's own filter decodes a title only when it holds a tag -- so
"nuts & b" and "o'neill" found nothing, and a facet option read "Fixings &amp; Fasteners".

This suite has no JavaScript engine, so the behaviour itself is checked in a browser against
the example page (cards_examples:treegrid_escaped_text). What is pinned here is that the page
carries the escaped values that exercise it, and that the shared script keeps clear of the
two things that broke it or would turn the fix into a hole: a string handed to fancytree's
filter, and markup parsed by innerHTML on an element of the page, which loads and runs what
it is given.
"""
import json
import re

from django.test import TestCase

from cards_examples.tests import FACTORY
from cards_examples.tests.test_treegrid import TreegridViewTestMixin
from cards_examples.views.treegrid import TreegridEscapedTextExample


class TestTreegridSearchesTheTextItShows(TreegridViewTestMixin, TestCase):
    view_class = TreegridEscapedTextExample

    def _configs(self, html):
        """Each card's static nodes and columns, read back the way the browser reads them."""
        return [(json.loads(nodes), json.loads(columns)) for nodes, columns in re.findall(
            r'^ +static_data: ([^\n]*),$.*?^ +columns: ([^\n]*),$', html, re.M | re.S)]

    def _shared_script(self):
        """The behaviour every grid on the page shares, emitted once."""
        html = self._render()
        start = html.index(FACTORY)
        return html[start:html.index('</script>', start)]

    def test_both_grids_render(self):
        html = self._render()
        self.assertIn('id="escaped_tree_table"', html)
        self.assertIn('id="escaped_paged_table"', html)

    def test_titles_and_html_cells_arrive_escaped(self):
        """The example is only a test of the fix while what it sends is escaped."""
        configs = self._configs(self._render())
        self.assertEqual(len(configs), 2)
        for nodes, _columns in configs:
            titles = [n['title'] for n in nodes]
            self.assertIn('Nuts &amp; Bolts', titles)
            self.assertIn('O&#x27;Neill&#x27;s Hinges', titles)
            self.assertIn('Less &lt;b&gt; more', titles)
            self.assertIn('<i class="fas fa-link"></i> Hooks &amp; Eyes', titles)
            # A tag partway through: "screws & p" crosses it, in the search and its highlight.
            self.assertIn('Screws <b>&amp;</b> Plugs', titles)
            self.assertIn('Fixings &amp; Fasteners', [n['data']['section'] for n in nodes])

    def test_a_text_column_is_sent_as_it_is(self):
        """Code is drawn as text, so its value is what shows -- and what is matched."""
        nodes, columns = self._configs(self._render())[0]
        self.assertIn('W&S-05', [n['data']['code'] for n in nodes])
        self.assertNotIn('type', next(c for c in columns if c['field'] == 'code'))

    def test_the_section_column_is_markup(self):
        _nodes, columns = self._configs(self._render())[0]
        self.assertEqual(next(c for c in columns if c['field'] == 'section')['type'], 'html')

    def test_search_hands_fancytree_a_function(self):
        """A string reaches fancytree's own matcher, which reads an escaped title raw."""
        calls = re.findall(r'\.filterNodes\(\s*(\w+)', self._shared_script())
        self.assertTrue(calls)
        self.assertEqual(set(calls), {'function'})

    def test_no_markup_is_parsed_into_an_element_of_the_page(self):
        """Decoding a value for search must not load or run it, so it goes through DOMParser."""
        script = self._shared_script()
        self.assertIn('new DOMParser()', script)
        self.assertNotRegex(script, r'\.innerHTML\s*=(?!=)')
