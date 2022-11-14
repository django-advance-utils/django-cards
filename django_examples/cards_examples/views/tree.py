from cards_examples.models import Company
from cards_examples.views.base import MainMenu
from django.views.generic import TemplateView
from django_menus.menu import MenuItem

from cards.tree_list import CardTree


class DjangoCardTree(MainMenu, CardTree, TemplateView):
    template_name = 'cards_examples/cards.html'


class ExampleCompanyTree(DjangoCardTree):
    list_title = 'Companies'
    model = Company

    def get_details_title(self, details_object):
        return f'Details {details_object.pk} adv'

    def get_tree_data(self):
        return [
            {"id": "ajson1", "parent": "#", "text": "Simple root node", "default": True},
            {"id": "ajson2", "parent": "#", "text": "Root node 2"},
            {"id": "ajson3", "parent": "ajson2", "text": "Child 1"},
            {"id": "ajson4", "parent": "ajson2", "text": "Child 2"},
        ]

    def setup_details_cards(self, details_object):
        card = self.add_main_card(details_object=details_object)
        card.add_rows(['name', 'active'],
                      [{'field': 'company_category__name', 'label': 'category'}],
                      'importance',
                      {'field': 'importance'},
                      'get_display_name')
        card2 = self.add_detail_card(show_created_modified_dates=False,
                                     details_object=details_object,
                                     title='Just Name')
        card2.add_rows('name')



