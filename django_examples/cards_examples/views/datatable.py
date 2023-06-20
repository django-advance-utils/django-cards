from cards_examples.models import Company
from cards_examples.models import CompanyCategory
from cards_examples.views.base import MainMenu
from django.views.generic import TemplateView
from django_datatables.columns import ColumnBase

from cards.base import CARD_TYPE_DATATABLE
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
                                          # 'pivot_filter_class': 'col-4 float-left',
                                          # 'pivot_table_class': 'col-8 col-4 float-left'
                                          })

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
