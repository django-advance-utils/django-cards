from ajax_helpers.mixins import AjaxHelpers
from cards_examples.models import Company, Person
from django.views.generic import TemplateView
from django_menus.menu import MenuMixin, MenuItem

from cards.base import CARD_TYPE_DATATABLE, CARD_TYPE_HTML
from cards.card_list import CardList
from cards.standard import CardMixin


class MainMenu(AjaxHelpers, MenuMixin):
    def setup_menu(self):
        # noinspection PyUnresolvedReferences
        self.add_menu('main_menu').add_items(
            ('cards_examples:index', 'Home'),
            ('cards_examples:groups', 'Groups'),
            ('cards_examples:list,-', 'List'),
            ('cards_examples:list_adv,-', 'List Adv'),
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

        card = self.add_card('welcome2', title='Welcome Two',
                             template_name='table', extra_card_context={'table_css_class': 'table-bordered'})
        card.add_entry(value='Welcome using the table template2', label='Sample')
        card.add_entry(value='This is some sample text2', label='Text')


class ExampleCardsIndex(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):

        self.add_welcome_card()
        self.add_person_card()
        self.add_company_card()
        self.add_companies_card()
        self.add_no_modal_card()
        self.add_html_card()

        self.add_card_group('welcome', 'person', div_css_class='col-6 float-left')
        self.add_card_group('company', 'companies', 'no_model', 'html', div_css_class='col-6 float-right')

    def add_welcome_card(self):
        card = self.add_card('welcome', title='Welcome')
        card.add_entry(value='sample text', label='Sample')

    def add_html_card(self):
        self.add_card('html', title='HTML sample', group_type=CARD_TYPE_HTML, html='<h1>Hello</h2>')

    @staticmethod
    def test_method(value):
        return f'<i>{value}</i>'

    def add_company_card(self):
        company = Company.objects.first()
        if company is None:
            card = self.add_card('company', title='Company')
            card.add_entry(value='Warning No Companies in the system', label=None,
                           html_override='<div class="alert alert-warning">%1%</div>')
        else:
            card = self.add_card('company', title='Company', details_object=company, show_created_modified_dates=True)
            card.add_rows(['name', 'active'],
                          [{'field': 'company_category__name', 'label': 'category'}],
                          'importance',
                          {'field': 'importance'},
                          {'field': 'get_display_name', 'label': 'Display Name'})

            card.add_entry(field='name', value_method=self.test_method)

            card.add_entry(value=['a', 'b'], label='test', html_override="<b>%1%</b>")

    def add_companies_card(self):
        self.add_card('companies', title='Company', group_type=CARD_TYPE_DATATABLE, datatable_model=Company)

    # noinspection PyMethodMayBeStatic
    def setup_table_companies(self, table, details_object):
        table.add_columns(
            'id',
            'name')

    def add_no_modal_card(self):
        self.add_card('no_model', title='No Model', group_type=CARD_TYPE_DATATABLE, datatable_model=None)

    # noinspection PyUnusedLocal
    def setup_table_no_model(self, table, details_object):
        table.add_columns(
            'id',
            'name')
        table.table_data = [{'id': 1, 'name': 'Tom Turner'}, ]

    def add_person_card(self):
        person = Person.objects.first()
        if person is None:
            card = self.add_card('person', title='Person')
            card.add_entry(value='Warning No People in the system', label=None,
                           html_override='<div class="alert alert-warning">%1%</div>')
        else:
            card = self.add_card('person', title='Person', details_object=person, show_created_modified_dates=True)
            card.add_rows('title',
                          'first_name',
                          'surname',
                          )


class ExampleCompanyCardList(MainMenu, CardList):
    list_title = 'Companies'
    model = Company

    def get_details_title(self, details_object):
        return f'Details {details_object.pk}'

    def get_details_data(self, card, details_object):
        card.add_rows(['name', 'active'],
                      [{'field': 'company_category__name', 'label': 'category'}],
                      'importance',
                      {'field': 'importance'},
                      'get_display_name')


class ExampleCompanyCardAdvancedList(MainMenu, CardList):
    list_title = 'Companies'
    model = Company

    def setup_details_cards(self, details_object):
        card = self.add_card(details_object=details_object, title='Details')
        card.add_rows(['name', 'active'],
                      [{'field': 'company_category__name', 'label': 'category'}],
                      'importance',
                      {'field': 'importance'},
                      'get_display_name')
        card2 = self.add_card(show_created_modified_dates=False, details_object=details_object, title='Just Name')
        card2.add_rows('name')


