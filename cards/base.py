import datetime

from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django_datatables.datatables import DatatableTable
from django_datatables.plugins.reorder import Reorder
from django_datatables.reorder_datatable import OrderedDatatable
from django_menus.menu import HtmlMenu

CARD_TYPE_STANDARD = 1
CARD_TYPE_DATATABLE = 2
CARD_TYPE_ORDERED_DATATABLE = 3
CARD_TYPE_HTML = 4


class CardBase:
    templates = {'default': {'name': 'cards/standard/default.html',
                             'context': {'card_css_class': 'card django-card',
                                         'card_body_css_class': 'card-body cards-list'}},
                 'table': {'name': 'cards/standard/table.html',
                           'context': {'card_css_class': 'card django-card',
                                       'card_body_css_class': 'card-body cards-list',
                                       'table_css_class': 'table'}},
                 'datatable': {'name': 'cards/standard/datatable.html',
                               'context': {'card_css_class': 'card django-card',
                                           'card_body_css_class': 'card-body cards-list'}},
                 'html': {'name': 'cards/standard/html.html',
                          'context': {'card_css_class': 'card django-card',
                                      'card_body_css_class': 'card-body cards-list'}}}

    ajax_commands = ['datatable']

    template_defaults = {CARD_TYPE_STANDARD: 'default',
                         CARD_TYPE_DATATABLE: 'datatable',
                         CARD_TYPE_ORDERED_DATATABLE: 'datatable',
                         CARD_TYPE_HTML: 'html'}

    def __init__(self, request, code, view=None, details_object=None, title=None, menu=None, template_name=None,
                 group_type=CARD_TYPE_STANDARD, show_created_modified_dates=False,
                 footer=None, extra_card_context=None, **kwargs):

        self.code = code
        self.view = view
        self.details_object = details_object
        self.request = request
        self.group_type = group_type
        self.show_created_modified_dates = show_created_modified_dates
        self.footer = footer

        self.rows = []
        self.title = title
        self.created_modified_dates = self.get_created_modified_dates(details_object=details_object)
        if isinstance(menu, (list, tuple)):
            menu = HtmlMenu(self.request, 'button_group').add_items(*menu)

        self.menu = menu
        self.extra_card_context = extra_card_context
        self.template_name = template_name
        self.extra_card_info = {}
        self.add_extra_card_info(extra_info=self.extra_card_info, group_type=self.group_type, **kwargs)

        self.process_data()

    # noinspection PyMethodMayBeStatic
    def add_extra_card_info(self, extra_info, group_type,  **kwargs):
        if group_type in (CARD_TYPE_DATATABLE, CARD_TYPE_ORDERED_DATATABLE):
            extra_info['datatable_id'] = kwargs.get('datatable_id', self.code)
            extra_info['datatable'] = kwargs.get('datatable')
            extra_info['datatable_model'] = kwargs.get('datatable_model')
            if group_type == CARD_TYPE_ORDERED_DATATABLE:
                extra_info['order_field'] = kwargs.get('order_field', 'order')
        elif group_type == CARD_TYPE_HTML:
            extra_info['html'] = kwargs.get('html')

    def add_boolean_entry(self, value, label=None, hidden=False, html_override=None,
                          entry_css_class=None, css_class=None):
        if value:
            entry = self._add_entry_internal(value='<i class="fas fa-check" style="color:green;"></i>',
                                             label=label,
                                             hidden=hidden,
                                             html_override=html_override,
                                             entry_css_class=entry_css_class,
                                             css_class=css_class)
        else:
            entry = self._add_entry_internal(value='<i class="fas fa-times" style="color:red;"></i>',
                                             label=label,
                                             hidden=hidden,
                                             html_override=html_override,
                                             entry_css_class=entry_css_class,
                                             css_class=css_class)
        return entry

    def add_date_entry(self, value, label=None, hidden=False, html_override=None, entry_css_class=None, css_class=None):
        new_value = value.strftime('%d/%m/%y')
        return self._add_entry_internal(value=new_value,
                                        label=label,
                                        hidden=hidden,
                                        html_override=html_override,
                                        entry_css_class=entry_css_class,
                                        css_class=css_class)

    def add_row(self, *args):

        entries = []
        for arg in args:
            if isinstance(arg, str):
                entry = self._add_entry_internal(field=arg)
            else:
                entry = self._add_entry_internal(**arg)
            if entry is not None:
                entries.append(entry)

        if (entry_len := len(entries)) > 0:
            if entry_len == 1:
                row = {'type': 'standard', 'entries': entries}
            else:
                css_types = {2: 'col-sm-6', 3: 'col-sm-4', 4: 'col-sm-3'}
                entry_css_class = css_types.get(entry_len, 'col-sm-6')

                for entry in entries:
                    if entry.get('entry_css_class') is None:
                        entry['entry_css_class'] = entry_css_class

                row = {'type': 'multiple', 'entries': entries}
            self.rows.append(row)

    def add_entry(self, value=None, field=None, label=None, entry_css_class=None, css_class=None,
                  default='N/A', link=None,  hidden=False, hidden_if_blank_or_none=False,
                  html_override=None, value_method=None, value_type=None, **kwargs):

        entry = self._add_entry_internal(value=value,
                                         field=field,
                                         label=label,
                                         entry_css_class=entry_css_class,
                                         css_class=css_class,
                                         default=default,
                                         link=link,
                                         hidden=hidden,
                                         hidden_if_blank_or_none=hidden_if_blank_or_none,
                                         html_override=html_override,
                                         value_method=value_method,
                                         value_type=value_type,
                                         **kwargs)
        if entry is not None:
            self.rows.append({'type': 'standard', 'entries': [entry]})

    def get_field_value(self, value, field, label):

        if value is None and field is not None:
            details_object = self.details_object
            if details_object is not None:
                value = details_object
                old_value = None
                parts = field.split('__')
                try:
                    for part in parts:
                        old_value = value
                        value = getattr(value, part)
                except AttributeError:
                    value = None

                if old_value is not None and len(parts) > 0:
                    try:
                        value = getattr(old_value, f'get_{parts[-1]}_display')
                    except AttributeError:
                        pass
                if not hasattr(value, 'through') and callable(value):
                    value = value()

                if label is None:
                    label = self.label_from_field(field=field)
        return value, label

    def _add_many_to_many_field(self, label, query, query_filter, m2m_field,
                                html_barge, default='N/A', html_override=None,
                                entry_css_class=None, css_class=None):
        if html_barge is None:
            html_barge = '<span class="small badge badge-pill badge-primary"> %1% </span> '

        if query_filter is None:
            results = query.all()
        else:
            results = query.filter(**query_filter)
        html = ''
        for result in results:
            if m2m_field is None:
                value = result
            else:
                value = hasattr(result, m2m_field)
                value = callable(value)
            html += html_barge.replace('%1%', str(value))

        return self._add_entry_internal(label=label,
                                        value=html,
                                        default=default,
                                        html_override=html_override,
                                        entry_css_class=entry_css_class,
                                        css_class=css_class)

    def _add_entry_internal(self, value=None, field=None, label=None, default='N/A', link=None,
                            hidden=False, hidden_if_blank_or_none=False, html_override=None,
                            value_method=None, value_type=None,
                            entry_css_class=None, css_class=None,
                            **kwargs):

        value, label = self.get_field_value(value=value, field=field, label=label)

        if hidden or (hidden_if_blank_or_none and (value is None or value == '')):
            return None
        if isinstance(value, bool):
            return self.add_boolean_entry(value=value,
                                          label=label,
                                          hidden=hidden,
                                          html_override=html_override,
                                          entry_css_class=entry_css_class,
                                          css_class=entry_css_class)
        elif isinstance(value, datetime.date):
            return self.add_date_entry(value=value, label=label, hidden=hidden, html_override=html_override)
        elif hasattr(value, 'through'):
            return self._add_many_to_many_field(label=label,
                                                query=value,
                                                query_filter=kwargs.get('query_filter'),
                                                html_barge=kwargs.get('html_barge'),
                                                m2m_field=kwargs.get('m2m_field'),
                                                default=default,
                                                html_override=html_override,
                                                entry_css_class=entry_css_class,
                                                css_class=entry_css_class)
        else:
            if value is None or value == '':
                value = default
            multiple_lines = isinstance(value, (list, tuple))

            if value_method is not None:
                if multiple_lines:
                    value = [value_method(v) for v in value]
                else:
                    value = value_method(value)
            if value_type is not None:
                if multiple_lines:
                    value = [self.get_value_from_type(v, value_type, **kwargs) for v in value]
                else:
                    value = self.get_value_from_type(value, value_type, **kwargs)
            if html_override is not None:
                if multiple_lines:
                    value = [html_override.replace('%1%', str(v)) for v in value]
                else:
                    value = html_override.replace('%1%', str(value))

            entry = {'label': label,
                     'html': value,
                     'entry_css_class': entry_css_class,
                     'css_class': css_class,
                     'multiple_lines': multiple_lines,
                     'link': link}
            return entry

    def get_value_from_type(self, value, value_type, **kwargs):
        # used if you override the class and want to do something with certain type of fields
        return value

    def process_data(self):
        if (self.group_type in (CARD_TYPE_DATATABLE, CARD_TYPE_ORDERED_DATATABLE) and
                self.extra_card_info['datatable'] is None):

            datatable_model = self.extra_card_info['datatable_model']
            table_id = self.extra_card_info['datatable_id']
            if self.extra_card_info['datatable'] is None:
                if self.group_type == CARD_TYPE_ORDERED_DATATABLE:
                    table = self.add_ordered_table(table_id=table_id,
                                                   model=datatable_model,
                                                   order_field=self.extra_card_info['order_field'])
                else:
                    table = self.add_table(table_id=table_id, model=datatable_model)
                self.extra_card_info['datatable'] = table
            else:
                table = self.extra_card_info['datatable']
            setup_table_field = 'setup_table'
            if self.code is not None:
                field_setup_table_field = f'setup_table_{self.code}'
                if hasattr(self.view, field_setup_table_field):
                    setup_table_field = field_setup_table_field

            getattr(self.view, setup_table_field)(details_object=self.details_object, table=table)

    def add_table(self, model, table_id=None):
        table = DatatableTable(table_id=table_id, model=model, view=self.view)
        self.extra_card_info['datatable'] = table
        table.ajax_data = False
        return table

    def add_ordered_table(self, model, order_field, table_id=None):
        table = OrderedDatatable(table_id=table_id,
                                 model=model,
                                 view=self.view,
                                 order_field=order_field)
        table.add_plugin(Reorder)
        table.ajax_data = False
        self.extra_card_info['datatable'] = table
        return table

    def get_created_modified_dates(self, details_object):
        if (self.show_created_modified_dates and details_object and
                hasattr(details_object, 'created') and hasattr(details_object, 'modified')):
            return details_object.created, details_object.modified
        return None

    def datatable_sort(self, **kwargs):
        order_field = self.extra_card_info['order_field']
        ids = [x[1] for x in kwargs['sort']]
        current_sort = dict(self.extra_card_info['datatable_model'].objects.filter(id__in=ids).
                            values_list('id', order_field))
        for s in kwargs['sort']:
            if current_sort[s[1]] != s[0]:
                o = self.extra_card_info['datatable_model'].objects.get(id=s[1])
                setattr(o, order_field, s[0])
                o.save()
        return self.command_response('null')

    @staticmethod
    def label_from_field(field):
        if type(field) == str and len(field) > 0:
            field_no_path = field.split('/')[-1].split('__')[-1]
            if field_no_path.find('_') > 0:
                return field_no_path.replace('_', ' ').title()
            else:
                title = field_no_path[0].upper()
                for letter in field_no_path[1:]:
                    if letter.isupper():
                        title += ' '
                    title += letter
                return title

    def add_rows(self, *args, default='N/A', hidden=False):
        for arg in args:
            if isinstance(arg, str):
                self.add_entry(field=arg, default=default, hidden=hidden)
            elif isinstance(arg, dict):
                if 'default' not in arg:
                    arg['default'] = default
                if 'hidden' not in arg:
                    arg['hidden'] = hidden
                self.add_entry(**arg)
            elif isinstance(arg, (list, tuple)):
                self.add_row(*arg)

    def render(self):
        extra_card_context = self.extra_card_context

        context = {'card': self,
                   'request': self.request,
                   'card_types': {'standard': CARD_TYPE_STANDARD,
                                  'datatable': CARD_TYPE_DATATABLE,
                                  'ordered_datatable': CARD_TYPE_ORDERED_DATATABLE,
                                  'html': CARD_TYPE_HTML}}

        if extra_card_context is not None:
            context = {**context, **extra_card_context}

        template_name = self.template_name
        if template_name is None:
            template_name = self.template_defaults.get(self.group_type)

        if template_name in self.templates:
            template = self.templates[template_name]['name']
            if 'context' in self.templates[template_name]:
                context = {**context, **self.templates[template_name]['context']}
        else:
            template = template_name

        data = render_to_string(template, context)
        return mark_safe(data)
