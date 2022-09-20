from ajax_helpers.mixins import AjaxHelpers
from django.views.generic import TemplateView
from django_menus.menu import MenuMixin, MenuItem

from cards.base import CardBase
from cards.card_list import CardList
from cards.standard import CardMixin
from cards_examples.models import Company, Person


class MainMenu(AjaxHelpers, MenuMixin):
    def setup_menu(self):
        # noinspection PyUnresolvedReferences
        self.add_menu('main_menu').add_items(
            ('cards_examples:index', 'Home'),
            ('cards_examples:groups', 'Groups'),
            ('cards_examples:list,-', 'List'),
            MenuItem(url='admin:index',
                     menu_display='Admin',
                     visible=self.request.user.is_superuser),

        )


class ExampleIndex(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/index.html'

    def setup_cards(self):

        card = self.add_card('welcome', title='Welcome')
        card.add_entry(value='Welcome using the default template', label='Sample')
        card.add_entry(value='This is some sample text', label='Text')

        card = self.add_card('welcome2', title='Welcome',
                             template_name='table', extra_card_context={'table_css_class': 'table-bordered'})
        card.add_entry(value='Welcome using the table template', label='Sample')
        card.add_entry(value='This is some sample text', label='Text')


class ExampleCardsIndex(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):

        self.add_welcome_card()
        self.add_person_card()
        self.add_company_card()
        self.add_companies_card()

        self.add_card_group('welcome', 'person', div_css_class='col-6 float-left')
        self.add_card_group('company', 'companies', div_css_class='col-6 float-right')

    def add_welcome_card(self):
        card = self.add_card('welcome', title='Welcome')
        card.add_entry(value='sample text', label='Sample')

    def add_company_card(self):
        company = Company.objects.first()
        if company is None:
            card = self.add_card('company', title='Company')
            card.add_entry(value='Warning No Companies in the system', label='Warning')
        else:
            card = self.add_card('company', title='Company', details_object=company, show_created_modified_dates=True)
            card.add_rows(['name', 'active'],
                          [{'field': 'company_category__name', 'label': 'category'}],
                          'importance',
                          {'field': 'importance'},
                          'get_display_name')

    def add_companies_card(self):
        self.add_card('companies', title='Company', group_type=CardBase.CARD_TYPE_DATATABLE, datatable_model=Company)

    def setup_table_companies(self, table, details_object):
        table.add_columns(
            'id',
            'name')

    def add_person_card(self):
        person = Person.objects.first()
        if person is None:
            card = self.add_card('person', title='Person')
            card.add_entry(value='Warning No People in the system', label='Warning')
        else:
            card = self.add_card('person', title='Person', details_object=person, show_created_modified_dates=True)
            card.add_rows('title',
                          'first_name',
                          'surname',
                          )


class ExampleCompanyCardList(MainMenu, CardList):
    list_title = 'Companies'
    model = Company

    def get_details_data(self, details_object, group_type):
        self.add_rows(['name', 'active'],
                      [{'field': 'company_category__name', 'label': 'category'}],
                      'importance',
                      {'field': 'importance'},
                      'get_display_name')
