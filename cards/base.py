import datetime

from django_datatables.datatables import DatatableTable
from django_datatables.reorder_datatable import OrderedDatatable
from django_menus.menu import HtmlMenu


class CardBase:

    GROUP_TYPE_STANDARD = 1
    GROUP_TYPE_DATATABLE = 2
    GROUP_TYPE_ORDERED_DATATABLE = 3
    GROUP_TYPE_HTML = 4

    ajax_commands = ['datatable']
    datatable_model = None
    datatable_order_field = 'order'

    def __init__(self):
        self.detail_groups = {}
        self.current_group = None
        self.tables = {}
        self.request = None
        super().__init__()

    def add_detail_group(self, code, title, menu=None, created_modified_dates=None, group_type=GROUP_TYPE_STANDARD):
        if menu is not None:
            details_menu = HtmlMenu(self.request, 'button_group').add_items(*menu)
        else:
            details_menu = None

        if group_type == self.GROUP_TYPE_STANDARD:
            self.detail_groups[code] = {'rows': [],
                                        'title': title,
                                        'created_modified_dates': created_modified_dates,
                                        'menu': details_menu,
                                        'type': group_type}
        elif group_type in (self.GROUP_TYPE_DATATABLE, self.GROUP_TYPE_ORDERED_DATATABLE):
            self.detail_groups[code] = {'table': None,
                                        'title': title,
                                        'created_modified_dates': created_modified_dates,
                                        'menu': details_menu,
                                        'type': group_type}
        elif group_type == self.GROUP_TYPE_HTML:
            self.detail_groups[code] = {'html': None,
                                        'title': title,
                                        'created_modified_dates': created_modified_dates,
                                        'menu': details_menu,
                                        'type': group_type}
        self.current_group = code

    def add_boolean_entry(self, value, label=None):
        if value:
            entry = self._add_entry_internal(value='<i class="fas fa-check" style="color:green;"></i>',
                                             label=label)
        else:
            entry = self._add_entry_internal(value='<i class="fas fa-times" style="color:red;"></i>',
                                             label=label)
        return entry

    def add_date_entry(self, value, label=None):
        new_value = value.strftime('%d/%m/%y')
        return self._add_entry_internal(value=new_value, label=label)

    def add_row(self, *args, css_class=None):

        entries = []
        for arg in args:
            entry = self._add_entry_internal(**arg)
            if entry is not None:
                entries.append(entry)

        if (entry_len := len(entries)) > 0:
            if entry_len == 1 and css_class is None:
                entry = {'type': 'standard', 'entries': entries}
            else:
                if css_class is None:
                    css_types = {2: 'col-sm-6', 3: 'col-sm-4', 4: 'col-sm-3'}
                    css_class = css_types.get(entry_len, 'col-sm-6')

                entry = {'type': 'multiple', 'entries': entries, 'css_class': css_class}
            self.detail_groups[self.current_group]['rows'].append(entry)

    def add_entry(self, value, label=None, css_class=None, default='N/A', link=None,
                  hidden=False, hidden_if_blank_or_none=False, html_override=None):

        entry = self._add_entry_internal(value=value,
                                         label=label,
                                         html_class=css_class,
                                         default=default,
                                         link=link,
                                         hidden=hidden,
                                         hidden_if_blank_or_none=hidden_if_blank_or_none,
                                         html_override=html_override)
        if entry is not None:
            self.detail_groups[self.current_group]['rows'].append({'type': 'standard', 'entries': [entry]})

    def _add_entry_internal(self, value, label=None, html_class=None, default='N/A', link=None,
                            hidden=False, hidden_if_blank_or_none=False, html_override=None):
        if hidden or (hidden_if_blank_or_none and (value is None or value == '')):
            return None
        if isinstance(value, bool):
            return self.add_boolean_entry(value=value, label=label)
        elif isinstance(value, datetime.date):
            return self.add_date_entry(value=value, label=label)
        else:
            if value is None or value == '':
                value = default
            multiple_lines = isinstance(value, (list, tuple))

            if html_override is not None:
                value = html_override.replace('%1%', str(value))

            entry = {'label': label, 'html': value, 'html_class': html_class,
                     'multiple_lines': multiple_lines, 'link': link}
            return entry

    def add_rows(self, *args, html_class=None, default='N/A', hidden=False):
        for arg in args:
            self.add_entry(value=arg[0], label=arg[1], css_class=html_class, default=default, hidden=hidden)

    def get_details_data(self, details_object, group_type):
        if group_type == self.GROUP_TYPE_DATATABLE:
            table = self.add_table(model=self.datatable_model)
            self.setup_table(details_object=details_object, table=table)
            self.detail_groups[self.current_group]['datatable'] = table
        elif group_type == self.GROUP_TYPE_ORDERED_DATATABLE:
            table = self.add_ordered_table(model=self.datatable_model, order_field=self.datatable_order_field)
            self.setup_table(details_object=details_object, table=table)
            self.detail_groups[self.current_group]['datatable'] = table

    def get_details_menu(self, details_object):
        return []

    def get_details_title(self, details_object):
        return "Details"

    def get_group_type(self, details_object):
        return self.GROUP_TYPE_STANDARD

    def add_table(self, model, table_id=None):
        table = DatatableTable(table_id=table_id, model=model, view=self)
        self.tables[table_id] = table
        return self.tables[table_id]

    def add_ordered_table(self, model, order_field, table_id=None):
        table = OrderedDatatable(table_id=table_id,
                                 model=model,
                                 view=self,
                                 order_field=order_field)
        self.tables[table_id] = table
        return self.tables[table_id]

    def setup_table(self, table, details_object):
        pass

    @staticmethod
    def get_created_modified_dates(details_object):
        if details_object and hasattr(details_object, 'created') and hasattr(details_object, 'modified'):
            return details_object.created, details_object.modified
        return None
