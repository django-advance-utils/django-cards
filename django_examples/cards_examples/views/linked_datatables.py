from cards_examples.models import Company, CompanyCategory, Person, Payment
from cards_examples.views.base import MainMenu
from django.views.generic import TemplateView
from django_menus.menu import MenuItem, AjaxButtonMenuItem

from cards.base import CARD_TYPE_LINKED_DATATABLES
from cards.standard import CardMixin


class LinkedDatatablesExample(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'

    ajax_commands = ['datatable', 'row']

    def setup_datatable_cards(self):
        self.add_linked_datatables_card(
            card_name='company_drilldown',
            title='Company Drilldown',
            datatables=[
                {'id': 'ld_categories', 'model': CompanyCategory, 'title': 'Categories',
                 'menu': [AjaxButtonMenuItem(button_name='add_category',
                                             menu_display='',
                                             font_awesome='fas fa-plus',
                                             css_classes='btn btn-sm btn-outline-success')]},
                {'id': 'ld_companies', 'model': Company, 'title': 'Companies',
                 'linked_field': 'company_category_id',
                 'menu': [AjaxButtonMenuItem(button_name='add_company',
                                             menu_display='',
                                             font_awesome='fas fa-plus',
                                             css_classes='btn btn-sm btn-outline-success')]},
                {'id': 'ld_people', 'model': Person, 'title': 'People',
                 'linked_field': 'company_id',
                 'row_link': 'admin:cards_examples_person_change',
                 'menu': [AjaxButtonMenuItem(button_name='add_person',
                                             menu_display='',
                                             font_awesome='fas fa-plus',
                                             css_classes='btn btn-sm btn-outline-success')]},
            ]
        )

    def button_add_category(self, **kwargs):
        return self.command_response('message', text='Add Category clicked')

    def button_add_company(self, **kwargs):
        return self.command_response('message', text='Add Company clicked')

    def button_add_person(self, **kwargs):
        return self.command_response('message', text='Add Person clicked')

    def setup_cards(self):
        self.add_card_group('company_drilldown', div_css_class='col-12 float-right')

    def setup_table_ld_categories(self, table, details_object):
        table.ajax_data = True
        table.add_columns('id', 'name')

    def setup_table_ld_companies(self, table, details_object):
        table.ajax_data = True
        table.add_columns('id', 'name', 'importance')

    def setup_table_ld_people(self, table, details_object):
        table.ajax_data = True
        table.add_columns('id', 'first_name', 'surname')


class LinkedDatatablesPaymentExample(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'

    ajax_commands = ['datatable', 'row']

    def setup_datatable_cards(self):
        self.add_linked_datatables_card(
            card_name='payment_drilldown',
            title='Payment Drilldown',
            datatables=[
                {'id': 'ld_pay_categories', 'model': CompanyCategory, 'title': 'Categories'},
                {'id': 'ld_pay_companies', 'model': Company, 'title': 'Companies',
                 'linked_field': 'company_category_id'},
                {'id': 'ld_pay_payments', 'model': Payment, 'title': 'Payments',
                 'linked_field': 'company_id'},
            ]
        )

    def setup_cards(self):
        self.add_card_group('payment_drilldown', div_css_class='col-12 float-right')

    def setup_table_ld_pay_categories(self, table, details_object):
        table.ajax_data = True
        table.add_columns('id', 'name')

    def setup_table_ld_pay_companies(self, table, details_object):
        table.ajax_data = True
        table.add_columns('id', 'name', 'importance')

    def setup_table_ld_pay_payments(self, table, details_object):
        table.ajax_data = True
        table.add_columns('id', 'date', 'amount', 'quantity')


class LinkedDatatablesFourLevelExample(MainMenu, CardMixin, TemplateView):
    """Example with 4 linked datatables to show it scales beyond 3.

    Category > Company > People and Payments both from Company.
    Demonstrates that the chain can go 4+ levels deep.
    """
    template_name = 'cards_examples/cards.html'

    ajax_commands = ['datatable', 'row']

    def setup_datatable_cards(self):
        self.add_linked_datatables_card(
            card_name='four_level',
            title='Four Level Drilldown',
            datatables=[
                {'id': 'ld4_categories', 'model': CompanyCategory, 'title': 'Categories'},
                {'id': 'ld4_companies', 'model': Company, 'title': 'Companies',
                 'linked_field': 'company_category_id'},
                {'id': 'ld4_people', 'model': Person, 'title': 'People',
                 'linked_field': 'company_id'},
                {'id': 'ld4_payments', 'model': Payment, 'title': 'Payments',
                 'linked_field': 'company_id'},
            ]
        )

    def setup_cards(self):
        self.add_card_group('four_level', div_css_class='col-12 float-right')

    def setup_table_ld4_categories(self, table, details_object):
        table.ajax_data = True
        table.add_columns('id', 'name')

    def setup_table_ld4_companies(self, table, details_object):
        table.ajax_data = True
        table.add_columns('id', 'name', 'importance')

    def setup_table_ld4_people(self, table, details_object):
        table.ajax_data = True
        table.add_columns('id', 'first_name', 'surname')

    def setup_table_ld4_payments(self, table, details_object):
        table.ajax_data = True
        table.add_columns('id', 'date', 'amount', 'quantity')

    def get_ld4_payments_query(self, table, **kwargs):
        """Custom query: when clicking a Person, find their company's payments."""
        person_id = self.request.POST.get('linked_filter_value')
        if person_id:
            try:
                person = Person.objects.get(id=person_id)
                if person.company_id:
                    table.filter['company_id'] = person.company_id
            except Person.DoesNotExist:
                pass
        return table.get_query(**kwargs)
