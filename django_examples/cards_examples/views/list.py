import random

from cards_examples.models import Company
from cards_examples.views.base import MainMenu
from django.views.generic import TemplateView
from django_menus.menu import MenuItem, AjaxButtonMenuItem

from cards.card_list import CardList


class DjangoCardList(MainMenu, CardList, TemplateView):
    template_name = 'cards_examples/cards.html'


class ExampleCompanyCardList(DjangoCardList):
    list_title = 'Companies'
    model = Company

    def get_details_menu(self, details_object):
        return [MenuItem('cards_examples:hello_modal', menu_display='Hello Modal'),
                MenuItem('cards_examples:hello_modal', menu_display='Hello Modal2'),
                AjaxButtonMenuItem(button_name='reload',
                                   menu_display='Reload',
                                   css_classes='btn btn-secondary')]

    def get_details_title(self, details_object):
        return f'Details {details_object.pk}'

    def get_details_data(self, card, details_object):
        number = random.randint(1, 1000)

        card.add_rows(['name', 'active'],
                      [{'field': 'company_category__name', 'label': 'Category'}],
                      'importance',
                      {'field': 'importance'},
                      'get_display_name',
                      {'value': number, 'label': 'Random'})

    # @ConfirmAjaxMethod(message="Would you like to reload the main card")
    def button_reload(self, *args, **kwargs):
        return self.command_response('load_details')


class ExampleCompanyCardEmptyList(ExampleCompanyCardList):
    def get_list_entries(self):
        return self.model.objects.all().filter(pk=999999)


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
