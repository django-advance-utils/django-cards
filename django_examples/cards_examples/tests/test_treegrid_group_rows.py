"""Group band rows: ``'_row_group': True`` in a node's data draws it as a heading band.

This suite has no JavaScript engine, so the band itself is checked in a browser against the
example page (cards_examples:treegrid_group_rows). What is pinned here is that the page sends the
flag, that the shared script turns it into the row class -- through applyRowClass, so it survives
fancytree's re-render of the row -- and that the grid's stylesheet draws that class from the
--django-card-treegrid-group-* variables.
"""
import json
import re

from django.test import TestCase

from cards_examples.tests import FACTORY
from cards_examples.tests.test_treegrid import TreegridViewTestMixin
from cards_examples.views.treegrid import TreegridGroupRowsExample


class TestTreegridGroupRows(TreegridViewTestMixin, TestCase):
    view_class = TreegridGroupRowsExample

    def _static_data(self, html):
        return [json.loads(nodes) for nodes in re.findall(r'^ +static_data: ([^\n]*),$', html, re.M)]

    def test_both_grids_render(self):
        html = self._render()
        self.assertIn('id="group_tasks_table"', html)
        self.assertIn('id="group_prices_table"', html)

    def test_the_bands_carry_the_flag(self):
        tasks, prices = self._static_data(self._render())
        self.assertTrue(all(node['data']['_row_group'] for node in tasks))
        self.assertTrue(all(not child['data'].get('_row_group') for node in tasks for child in node['children']))
        # A heading between the rows of a flat list, with nothing under it.
        bands = [node for node in prices if node['data'].get('_row_group')]
        self.assertEqual([band['title'] for band in bands], ['Timber', 'Glass', 'Ironmongery'])
        self.assertTrue(all('children' not in band for band in bands))

    def test_the_script_turns_the_flag_into_the_row_class(self):
        html = self._render()
        start = html.index(FACTORY)
        script = html[start:html.index('</script>', start)]
        self.assertIn("if (d._row_group) applyRowClass(node, $tr, 'treegrid-group-row');", script)

    def test_the_band_is_drawn_from_the_variables(self):
        html = self._render()
        self.assertIn('.fancytree-ext-table tbody tr.treegrid-group-row > td', html)
        for name in ('bg', 'color', 'gap', 'hover-color', 'font-weight', 'letter-spacing'):
            self.assertIn(f'--django-card-treegrid-group-{name}', html)
        # The title's colour is the skin's own unless the band hands it down.
        self.assertIn('tr.treegrid-group-row > td span.fancytree-title', html)
