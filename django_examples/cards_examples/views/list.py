from cards_examples.models import Company
from cards_examples.views.base import MainMenu
from django.views.generic import TemplateView
from django_menus.menu import MenuItem

from cards.card_list import CardList


class DjangoCardList(MainMenu, CardList, TemplateView):
    template_name = 'cards_examples/cards.html'


class ExampleCompanyCardList(DjangoCardList):
    list_title = 'Companies'
    model = Company

    def get_details_menu(self, details_object):
        return [MenuItem('cards_examples:hello_modal', menu_display='Hello Modal'),
                MenuItem('cards_examples:hello_modal', menu_display='Hello Modal2')]

    def get_details_title(self, details_object):
        return f'Details {details_object.pk}'

    def get_details_data(self, card, details_object):
        card.add_rows(['name', 'active'],
                      [{'field': 'company_category__name', 'label': 'Category'}],
                      'importance',
                      {'field': 'importance'},
                      'get_display_name')


class ExampleCompanyCardAdvancedList(DjangoCardList):
    list_title = 'Companies'
    model = Company

    def get_details_title(self, details_object):
        return f'Details {details_object.pk} adv'

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



