from cards_examples.models import Company, Person
from cards_examples.views.base import MainMenu
from django.views.generic import TemplateView
from django_menus.menu import MenuItem, HtmlMenu, AjaxButtonMenuItem

from cards.base import CARD_TYPE_DATATABLE
from cards.standard import CardMixin


class ExampleIndex(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/index.html'

    def setup_cards(self):

        card = self.add_card('welcome', title='Welcome', footer='This is a footer')
        card.add_entry(value='Welcome using the default template', label='Sample')
        card.add_entry(value='This is some sample text', label='Text')
        card.add_entry(value=self.ajax_btn(), label='Buttons')

        card = self.add_card('welcome2',
                             title='Welcome Two',
                             template_name='table',
                             extra_card_context={'table_css_class': 'table table-bordered'},
                             collapsed=False)
        card.add_entry(value='Welcome using the table template2', label='Sample')
        card.add_entry(value='This is some sample text2', label='Text')
        card.add_html_entry(template_name='cards_examples/sample_entry.html', colspan=2)

        card = self.add_card('welcome3',
                             title='Table Examples',
                             template_name='table',
                             extra_card_context={'table_css_class': 'table table-bordered'},
                             collapsed=False,
                             hidden_if_blank_or_none=True)

        card.add_entry(value='Description', label='Value', value_th=True, extra_cells=[''])

        card.add_rows(({'value': 'Welcome using the table template2',
                        'label': 'Sample', 'label_td': True},
                       {'value': 'Value 1-1'}),
                      {'value': '', 'label': 'This is hidden'},
                      {'value': 0.0, 'label': 'This is also hidden', 'hidden_if_zero': True},)
        card.add_entry(value='Welcome using the table template2', label='Total', value_th=True)

    def ajax_btn(self):
        ajax_btn = HtmlMenu(request=self.request, template='button_group') \
            .add_items(AjaxButtonMenuItem(button_name='message',
                                          menu_display='',
                                          font_awesome='fa fa-question',
                                          css_classes='btn btn-sm btn-primary')).render()
        return ajax_btn

    def button_message(self, **_kwargs):
        return self.command_response('message', text='Buttons')


class ExampleCardsIndex(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_welcome_card()
        self.add_split_card()
        self.add_table_multiple_columns()
        self.add_other_card()
        collapsed_card = self.add_collapsed_card()
        self.add_person_card()
        self.add_multi_fields_card()
        self.add_company_card()
        self.add_companies_card()
        self.add_no_modal_card()
        self.add_html_string_card()
        self.add_html_file_card()
        self.add_empty_message_card()

        self.add_card_group('welcome', 'split', 'table_multiple_columns',
                            'other', 'person', 'multi_fields_example', collapsed_card,
                            div_css_class='col-6 float-left', )
        self.add_card_group('company', 'companies', 'no_model', 'test_error_not_found',
                            div_css_class='col-6 float-right', error_if_not_found=False)
        self.add_card_group('html_string', 'html_file', 'empty_list_message', div_css_class='col-12 float-right')

    def add_welcome_card(self):
        menu = [MenuItem('cards_examples:hello_modal', menu_display='Hello Modal')]
        tab_menu = [('cards_examples:index', 'Home'),
                    ('cards_examples:groups', 'Groups')]
        card = self.add_card('welcome', title='Welcome', menu=menu, tab_menu=tab_menu)
        card.add_entry(value='sample text', label='Sample')

    def add_split_card(self):
        card = self.add_card('split', title='Split Column', collapsed=False)
        card.add_rows(({'value': 'Hello'}, {'value': 'World'}),
                      ({'value': 'Hello'}, {'value': 'World'}, {'value': ':)'}),
                      ({'value': 'Hello', 'entry_css_class': 'col-sm-9'},
                       {'value': 'World', 'entry_css_class': 'col-sm-3'}))

    def add_table_multiple_columns(self):
        card = self.add_card('table_multiple_columns',
                             title='Table Multiple Columns',
                             template_name='table',
                             extra_card_context={'table_css_class': 'table table-bordered'},
                             collapsed=False)
        card.add_rows(({'value': 'Value 1-0', 'label': 'Row 1'}, {'value': 'Value 1-1', 'colspan': 2}),
                      ({'value': 'Value 2-0', 'label': 'Row 2'}, {'value': 'Value 2-1'}, {'value': 'Value 2-2'}))

        card.add_rows({'value': 'Value 3-0', 'label': 'Row 3'},
                      {'value': 'Value 4-0', 'label': 'Row 4'}, extra_row_kwargs={'colspan': 3})

    def add_other_card(self):
        card = self.add_card('other', title='Other', collapsed=False)
        card.add_rows({'value': 'This should be in uppercase',
                       'label': 'CSS Class',
                       'css_class': 'text-uppercase'},
                      {'value': 'I am not shown', 'label': 'Hidden', 'hidden': True},
                      {'value': 'What message!!',
                       'label': 'Html Override',
                       'html_override': '<div class="alert alert-warning">%1%</div>'})

    def add_collapsed_card(self):
        card = self.add_card(title='Collapsed by default', collapsed=True)
        card.add_rows({'value': 'Boo'})
        return card

    def add_html_string_card(self):
        self.add_html_data_card(card_name='html_string',
                                title='HTML string sample',
                                html='<h1>Hello</h2>',
                                collapsed=False)

    def add_html_file_card(self):
        self.add_html_card(card_name='html_file',
                           title='HTML file card',
                           context_template_name='cards_examples/hello_world.html',
                           context={'from_view': 'this is from the view'})

    def add_empty_message_card(self):
        card = self.add_card('empty_list_message',
                             title='Empty Message',
                             is_empty=True,
                             empty_message='This is empty with is_empty=True',
                             collapsed=False)
        card.add_rows(({'value': 'Hello'}, {'value': 'World'}),
                      ({'value': 'Hello'}, {'value': 'World'}, {'value': ':)'}),
                      ({'value': 'Hello', 'entry_css_class': 'col-sm-9'},
                       {'value': 'World', 'entry_css_class': 'col-sm-3'}))

    @staticmethod
    def test_method(value):
        return f'<i>{value}</i>'

    def add_company_card(self):
        company = Company.objects.first()
        if company is None:
            card = self.add_card('company',
                                 title='Company',
                                 collapsed=False)
            card.add_entry(value='Warning No Companies in the system', label=None,
                           html_override='<div class="alert alert-warning">%1%</div>')
        else:
            card = self.add_card('company',
                                 title='Company',
                                 details_object=company,
                                 show_created_modified_dates=True,
                                 collapsed=False)
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
                      datatable_model=Company,
                      collapsed=False)

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
            menu = [MenuItem('cards_examples:hello_modal', menu_display='',
                             font_awesome='fas fa-edit', css_classes='btn btn-link')]
            card = self.add_card('person', title='Person', details_object=person, show_created_modified_dates=True)
            card.add_rows('title',
                          {'field': 'first_name', 'menu': menu},
                          'surname',
                          ('title', 'first_name', 'surname')
                          )
            card.add_html_entry(template_name='cards_examples/sample_entry.html')
            card.add_html_entry(template_name='cards_examples/sample_entry.html')

    def add_multi_fields_card(self):
        person = Person.objects.first()
        if person is None:
            card = self.add_card('multi_fields_example', title='Multi fields example')
            card.add_entry(value='Warning No People in the system', label=None,
                           html_override='<div class="alert alert-warning">%1%</div>')
        else:
            card = self.add_card('multi_fields_example', title='Multi fields example',
                                 details_object=person, show_created_modified_dates=True)
            card.add_rows({'field': ['title', 'first_name', 'surname'],
                           'label': 'Full name (multiline)'},
                          {'field': ['title', 'first_name', 'surname'],
                           'label': 'Full name (with merge=True)', 'merge': True},
                          {'field': ['title', 'first_name', 'surname'],
                           'label': 'Full name (with merge=True, merge_string=" - ")',
                           'merge': True, 'merge_string': ' - '},
                          {'field': ['age', 'id'], 'merge': True},
                          )
