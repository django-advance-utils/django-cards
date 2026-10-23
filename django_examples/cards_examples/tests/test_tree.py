"""The tree card loads a node's details unless the node is a group."""

import json
import re

from cards.card_list import CardTree
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.views.generic import TemplateView

PACKS = ('bootstrap4', 'bootstrap5')


class TestANodeSaysWhetherItIsAGroup(SimpleTestCase):
    """With ``show_details_for_parents`` off, a node with children used to be a group whatever it was.

    A node now says for itself with ``is_group`` on its dict; one that says nothing is a group when it has
    children, as before.
    """

    def tree_card_html(self, nodes, pack, show_details_for_parents=False):
        class _TreeView(CardTree, TemplateView):
            list_title = 'Tree'

            def get_tree_data(self, selected_id):
                return nodes

        _TreeView.show_details_for_parents = show_details_for_parents
        with override_settings(DJANGO_CARDS_TEMPLATE_PACK=pack):
            view = _TreeView()
            view.request = RequestFactory().get('/')
            view.setup_cards()
            return view.cards['tree_card'].render()

    NODES = [
        {'id': 'inbox', 'parent': '#', 'text': 'Inbox', 'is_group': False},
        {'id': 'inbox/receipts', 'parent': 'inbox', 'text': 'Receipts', 'is_group': False},
        {'id': 'archive', 'parent': '#', 'text': 'Archive', 'is_group': True},
        {'id': 'archive/2025', 'parent': 'archive', 'text': '2025'},
    ]

    def test_the_flag_reaches_the_page_and_the_script_reads_it(self):
        for pack in PACKS:
            with self.subTest(pack=pack):
                html = self.tree_card_html(self.NODES, pack)
                blob = re.search(r"'data': (\[.*?\]),\n", html, re.S).group(1)
                nodes = {node['id']: node for node in json.loads(blob)}
                self.assertIs(nodes['inbox']['is_group'], False)
                self.assertIs(nodes['archive']['is_group'], True)
                self.assertNotIn('is_group', nodes['archive/2025'])
                # The rule, where both the click and the first load read it: a stated flag decides, and only
                # a node that states nothing falls back to its children.
                self.assertIn('original.is_group === true || original.is_group === false', html)
                self.assertIn('return node.children.length === 0', html)
                self.assertIn('has_details(data.node)', html)
                self.assertIn('!selected || has_details(selected)', html)

    def test_show_details_for_parents_loads_every_node(self):
        for pack in PACKS:
            with self.subTest(pack=pack):
                html = self.tree_card_html(self.NODES, pack, show_details_for_parents=True)
                self.assertIn('return true;', html)
                self.assertNotIn('original.is_group', html)
