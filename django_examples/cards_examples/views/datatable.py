from cards_examples.models import Company, Status
from cards_examples.models import CompanyCategory
from cards_examples.views.base import MainMenu
from django.views.generic import TemplateView
from django_datatables.columns import ColumnBase

from cards.base import CARD_TYPE_DATATABLE, CARD_TYPE_ORDERED_DATATABLE
from cards.standard import CardMixin


class DatatableExample(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'

    ajax_commands = ['datatable', 'row', 'column']

    def setup_datatable_cards(self):
        self.add_companies_card()

    def setup_cards(self):
        self.add_card_group('companies', div_css_class='col-12 float-right')

    def add_companies_card(self):
        self.add_card('companies',
                      title='Company (Datatables)',
                      group_type=CARD_TYPE_DATATABLE,
                      datatable_model=Company,
                      extra_card_context={'show_search_bar': False,
                                          'show_pivot_table': True,
                                          'top': '<h5 style="padding-left: 10px">This is top</h5>',
                                          'bottom': '<h5 style="padding-left: 10px">This is bottom</h5>'
                                          # 'pivot_filter_class': 'col-4 float-left',
                                          # 'pivot_table_class': 'col-8 col-4 float-left'
                                          },
                      collapsed=False)

    def setup_table_companies(self, table, details_object):
        table.edit_fields = ['name', 'company_category__name']
        table.edit_options = {'company_category__name': {'select2': True}}

        table.ajax_data = True
        table.add_columns(
            'id',
            'name',
            'importance',
            ColumnBase(column_name='company_category__name',
                       field='name',
                       table=table, model=CompanyCategory))
        table.add_js_filters('pivot', 'importance', filter_title='Importance')


class DatatableOrderExample(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'

    ajax_commands = ['datatable', 'row', 'column']

    def setup_datatable_cards(self):
        self.add_status_card()

    def setup_cards(self):
        self.add_card_group('statuses', div_css_class='col-12 float-right')

    def add_status_card(self):
        self.add_card('statuses',
                      title='Statuses',
                      group_type=CARD_TYPE_ORDERED_DATATABLE,
                      datatable_model=Status,)

    def setup_table_statuses(self, table, details_object):


        table.ajax_data = True
        table.add_columns(
            'id',
            'name',
            )
