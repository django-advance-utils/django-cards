from cards_examples.models import Company, Person
from django.views.generic import TemplateView
from django_menus.menu import MenuItem

from cards.base import CARD_TYPE_DATATABLE, CARD_TYPE_HTML
from cards.standard import CardMixin
from cards_examples.views.base import MainMenu


class ExampleIndex(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/index.html'

    def setup_cards(self):

        card = self.add_card('welcome', title='Welcome', footer='This is a footer')
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
        self.add_split_card()
        self.add_other_card()
        self.add_person_card()
        self.add_company_card()
        self.add_companies_card()
        self.add_no_modal_card()
        self.add_html_string_card()
        self.add_html_file_card()

        self.add_card_group('welcome', 'split', 'other', 'person', div_css_class='col-6 float-left')
        self.add_card_group('company', 'companies',
                            'no_model', div_css_class='col-6 float-right')
        self.add_card_group('html_string', 'html_file',  div_css_class='col-12 float-right')

    def add_welcome_card(self):
        menu = [MenuItem('cards_examples:hello_modal', menu_display='Hello Modal')]
        tab_menu = [('cards_examples:index', 'Home'),
                    ('cards_examples:groups', 'Groups')]
        card = self.add_card('welcome', title='Welcome', menu=menu, tab_menu=tab_menu)
        card.add_entry(value='sample text', label='Sample')

    def add_split_card(self):
        card = self.add_card('split', title='Split Column')
        card.add_rows(({'value': 'Hello'}, {'value': 'World'}),
                      ({'value': 'Hello'}, {'value': 'World'}, {'value': ':)'}),
                      ({'value': 'Hello', 'entry_css_class': 'col-sm-9'},
                       {'value': 'World', 'entry_css_class': 'col-sm-3'}))

    def add_other_card(self):
        card = self.add_card('other', title='Other')
        card.add_rows({'value': 'This should be in uppercase',
                       'label': 'CSS Class',
                       'css_class': 'text-uppercase'},
                      {'value': 'I am not shown', 'label': 'Hidden', 'hidden': True},
                      {'value': 'What message!!',
                       'label': 'Html Override',
                       'html_override': '<div class="alert alert-warning">%1%</div>'})

    def add_html_string_card(self):
        self.add_card('html_string', title='HTML string sample', group_type=CARD_TYPE_HTML, html='<h1>Hello</h2>')

    def add_html_file_card(self):
        self.add_html_card('html_file', title='HTML string sample',
                           context_template_name='cards_examples/hello_world.html',
                           context={'from_view': 'this is from the view'})

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

            card.add_entry(field='sectors')

    def add_companies_card(self):
        self.add_card('companies',
                      title='Company (Datatables)',
                      group_type=CARD_TYPE_DATATABLE,
                      datatable_model=Company)

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