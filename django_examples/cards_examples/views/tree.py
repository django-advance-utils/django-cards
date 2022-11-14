from cards_examples.models import Company
from cards_examples.views.base import MainMenu
from django.views.generic import TemplateView

from cards.tree_list import CardTree


class DjangoCardTree(MainMenu, CardTree, TemplateView):
    template_name = 'cards_examples/cards.html'


class ExampleCompanyTree(DjangoCardTree):
    list_title = 'Tree'

    def get_details_title(self, details_object):
        return f'Details {details_object} tree'

    def get_default_selected_id(self):
        return 'ajson1'

    def get_tree_data(self, selected_id):
        return [
            {"id": "ajson1", "parent": "#", "text": "Simple root node"},
            {"id": "ajson2", "parent": "#", "text": "Root node 2"},
            {"id": "ajson3", "parent": "ajson2", "text": "Child 1"},
            {"id": "ajson4", "parent": "ajson2", "text": "Child 2"},
            {"id": "ajson5", "parent": "ajson4", "text": "Child 3"},
        ]

    def get_details_data(self, card, details_object):
        card.add_rows({'value': details_object, 'title': 'id'})


