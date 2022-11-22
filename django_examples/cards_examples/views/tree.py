from cards_examples.views.base import MainMenu
from django.templatetags.static import static
from django.views.generic import TemplateView

from cards.card_list import CardTree


class DjangoCardTree(MainMenu, CardTree, TemplateView):
    template_name = 'cards_examples/cards.html'


class ExampleCompanyTree(DjangoCardTree):
    list_title = 'Tree'

    def get_details_title(self, details_object):
        return f'Details {details_object} tree'

    def get_default_selected_id(self):
        return 'ajson1'

    def get_tree_data(self, selected_id):
        tree_data = [
            {"id": "ajson1", "parent": "#", "text": "Simple root node"},
            {"id": "ajson2", "parent": "#", "text": "Root node 2"},
            {"id": "ajson3", "parent": "ajson2", "text": "Child 1", 'icon': static('tree_icon.png')},
            {"id": "ajson4", "parent": "ajson2", "text": "Child 2"},
            {"id": "ajson5", "parent": "ajson4", "text": "Child 3", "icon": "fas fa-wrench"},
        ]

        for x in range(100):
            tree_data.append({'id': f'a{x}', 'parent': 'ajson4', 'text': f'demo {x}'})

        return tree_data

    def get_details_data(self, card, details_object):
        card.add_rows({'value': details_object, 'title': 'id'})
