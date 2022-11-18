import json

from django.views.generic import TemplateView
from django_datatables.columns import ColumnBase, DatatableColumnError, EDIT_SEND, EDIT_CELL_HTML
from django_datatables.helpers import render_replace

from cards.base import CARD_TYPE_DATATABLE
from cards.standard import CardMixin
from cards_examples.views.base import MainMenu

from cards_examples.models import Company

from cards_examples.models import CompanyCategory


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
                      datatable_model=Company)

    def setup_table_companies(self, table, details_object):
        table.edit_fields = ['name', 'company_category__name']
        table.edit_options = {'company_category__name': {'select2': True}}
        table.ajax_data = True
        table.add_columns(
            'id',
            'name',
            ColumnBase(column_name='company_category__name',
                       field='name',
                       table=table, model=CompanyCategory))
