import datetime
import json
from collections import defaultdict

from ajax_helpers.utils import random_string
from django.core.exceptions import FieldDoesNotExist
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
CARD_TYPE_LIST_SELECTION = 5
CARD_TYPE_CARD_GROUP = 6
CARD_TYPE_CARD_LAYOUT = 7


class CardBase:
    templates = {'default': {'name': 'cards/standard/default.html',
                             'context': {'card_css_class': 'card django-card',
                                         'card_body_css_class': 'card-body cards-list',
                                         'item_css_class': 'list-group-item'}},
                 'default_body': {'name': 'cards/standard/default_body.html',
                                  'context': {'card_body_css_class': 'card-body cards-list',
                                              'item_css_class': 'list-group-item'}},
                 'table': {'name': 'cards/standard/table.html',
                           'context': {'card_css_class': 'card django-card',
                                       'card_body_css_class': 'card-body cards-list',
                                       'table_css_class': 'table'}},
                 'table_body': {'name': 'cards/standard/table_body.html'},
                 'datatable': {'name': 'cards/standard/datatable.html',
                               'context': {'card_css_class': 'card django-card',
                                           'card_body_css_class': 'card-body cards-list'}},
                 'html': {'name': 'cards/standard/html.html',
                          'context': {'card_css_class': 'card django-card',
                                      'card_body_css_class': 'card-body cards-list'}},
                 'card_group': {'name': 'cards/standard/card_group.html',
                                'context': {'card_css_class': 'card django-card',
                                            'card_body_css_outer_class': 'card-body',
                                            'card_body_css_inner_class': 'row cards-list'}},
                 'card_layout': {'name': 'cards/standard/card_group.html',
                                 'context': {'card_body_css_outer_class': '',
                                             'card_css_class': '',
                                             'card_body_css_inner_class': 'row'}},
                 'list_selection': {'name': 'cards/standard/list_selection.html',
                                    'context': {'card_css_class': 'card django-card',
                                                'card_link_css_class': 'list-group-item cards-list-group-item',
                                                'card_body_css_class': 'overflow-auto',
                                                'card_body_css_style': 'height: calc(100vh - 150px);',
                                                'modal': False}},
                 'tree_selection': {'name': 'cards/standard/tree_selection.html',
                                    'context': {'card_css_class': 'card django-card',
                                                'card_body_css_class': 'card-body cards-list overflow-auto',
                                                'card_body_css_style': 'height: calc(100vh - 150px);',
                                                'tree_themes': json.dumps({'name': 'proton', 'responsive': True}),
                                                'tree_plugins': json.dumps(['wholerow'])}},
                 'blank': {'name': 'cards/standard/blank.html'},
                 'message': {'name': 'cards/standard/message.html',
                             'context': {'card_css_class': 'card django-card',
                                         'alert_css_class': 'alert-warning'}}}

    ajax_commands = ['datatable']

    template_defaults = {CARD_TYPE_STANDARD: 'default',
                         CARD_TYPE_DATATABLE: 'datatable',
                         CARD_TYPE_ORDERED_DATATABLE: 'datatable',
                         CARD_TYPE_HTML: 'html',
                         CARD_TYPE_LIST_SELECTION: 'list_selection',
                         CARD_TYPE_CARD_GROUP: 'card_group',
                         CARD_TYPE_CARD_LAYOUT: 'card_layout'}

    button_menu_type = 'button_group'
    tab_menu_type = 'tabs'
    default_empty_template = 'message'

    def __init__(self, request, code=None, view=None, details_object=None, title=None,
                 menu=None, tab_menu=None, template_name=None, call_details_data=False,
                 group_type=CARD_TYPE_STANDARD, show_created_modified_dates=False,
                 footer=None, extra_card_context=None,
                 is_empty=False, empty_template_name=None, empty_message='N/A',
                 collapsed=None, hidden_if_blank_or_none=None, **kwargs):

        if code is None:
            code = random_string()

        self.code = code
        self.view = view
        self.details_object = details_object
        self.request = request

        self.show_created_modified_dates = show_created_modified_dates
        self.footer = footer

        self.rows = []
        self._row_styles = {}
        self._default_row_styles = None
        if title is not None:
            self.title = mark_safe(title)
        else:
            self.title = None
        self.created_modified_dates = self.get_created_modified_dates(details_object=details_object)
        if isinstance(menu, (list, tuple)):
            menu = HtmlMenu(self.request, self.button_menu_type).add_items(*menu)
        self.menu = menu
        if isinstance(tab_menu, (list, tuple)):
            tab_menu = HtmlMenu(self.request, self.tab_menu_type).add_items(*tab_menu)
        self.tab_menu = tab_menu
        self.call_details_data = call_details_data
        self.enable_collapse = collapsed is not None
        self.collapsed = collapsed
        self.hidden_if_blank_or_none = hidden_if_blank_or_none

        if is_empty:
            self.group_type = CARD_TYPE_STANDARD
            self.extra_card_context = {'message': empty_message}
            if empty_template_name is None:
                self.template_name = self.default_empty_template
            else:
                self.template_name = empty_template_name
        else:
            self.extra_card_context = extra_card_context
            self.template_name = template_name
            self.group_type = group_type
        self.extra_card_info = {}
        self.add_extra_card_info(extra_info=self.extra_card_info, group_type=self.group_type, **kwargs)

        self.process_data()
        self.child_card_groups = []

    # noinspection PyMethodMayBeStatic
    def add_extra_card_info(self, extra_info, group_type,  **kwargs):
        if group_type in (CARD_TYPE_DATATABLE, CARD_TYPE_ORDERED_DATATABLE):
            extra_info['datatable_id'] = kwargs.get('datatable_id', self.code)
            extra_info['datatable'] = kwargs.get('datatable')
            extra_info['datatable_model'] = kwargs.get('datatable_model')
            extra_info['setup_table'] = kwargs.get('setup_table')
            if group_type == CARD_TYPE_ORDERED_DATATABLE:
                extra_info['order_field'] = kwargs.get('order_field', 'order')
        elif group_type == CARD_TYPE_HTML:
            extra_info['html'] = kwargs.get('html')

    def add_boolean_entry(self, value, label=None, hidden=False, html_override=None,
                          entry_css_class=None, css_class=None,
                          menu=None, default_if=None, value_type=None, row_style=None, **kwargs):
        if value:
            entry = self._add_entry_internal(value='<i class="fas fa-check" style="color:green;"></i>',
                                             label=label,
                                             hidden=hidden,
                                             html_override=html_override,
                                             entry_css_class=entry_css_class,
                                             css_class=css_class,
                                             menu=menu,
                                             default_if=default_if,
                                             value_type=value_type,
                                             row_style=row_style,
                                             **kwargs)
        else:
            entry = self._add_entry_internal(value='<i class="fas fa-times" style="color:red;"></i>',
                                             label=label,
                                             hidden=hidden,
                                             html_override=html_override,
                                             entry_css_class=entry_css_class,
                                             css_class=css_class,
                                             menu=menu,
                                             default_if=default_if,
                                             value_type=value_type,
                                             row_style=row_style,
                                             **kwargs)
        return entry

    def add_date_entry(self, value, label=None, hidden=False, html_override=None,
                       entry_css_class=None, css_class=None, menu=None, default_if=None,
                       value_type=None, row_style=None, **kwargs):
        new_value = value.strftime('%d/%m/%y')
        return self._add_entry_internal(value=new_value,
                                        label=label,
                                        hidden=hidden,
                                        html_override=html_override,
                                        entry_css_class=entry_css_class,
                                        css_class=css_class,
                                        menu=menu,
                                        default_if=default_if,
                                        value_type=value_type,
                                        row_style=row_style,
                                        **kwargs)

    def add_row(self, *args, extra_row_kwargs=None):
        if extra_row_kwargs is None:
            extra_row_kwargs = {}
        entries = []
        for arg in args:
            if isinstance(arg, str):
                entry = self._add_entry_internal(field=arg, **extra_row_kwargs)
            else:
                entry = self._add_entry_internal(**arg, **extra_row_kwargs)
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
                  default='N/A', link=None,  hidden=False, hidden_if_blank_or_none=None,
                  html_override=None, value_method=None, value_type=None, default_if=None, row_style=None, **kwargs):

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
                                         default_if=default_if,
                                         row_style=row_style,
                                         **kwargs)
        if entry is not None:
            self.rows.append({'type': 'standard', 'entries': [entry]})

    def add_html_entry(self, template_name, context=None, **kwargs):
        if context is None:
            context = {}
        context = {**context, **kwargs}
        html = render_to_string(template_name=template_name, context=context)
        self.rows.append({'type': 'html', 'html': html, **kwargs})

    def add_row_style(self, name, html, is_default=False):
        if not isinstance(html, str) and hasattr(html, 'render'):
            html = html.render()
        self._row_styles[name] = html
        if is_default:
            self._default_row_styles = name

    def set_default_style(self, name=None):
        if name in self._row_styles:
            self._default_row_styles = name

    def get_field_value(self, value, field, label):
        field_type = None
        if value is None and field is not None:
            if isinstance(field, (list, tuple)):
                values = []
                field_type = []
                for _field in field:
                    _value, _label, _field_type = self.get_field_value(value=None, field=_field, label=label)
                    if not label:
                        label = _label
                    values.append(_value)
                    field_type.append(_field_type)
                value = values
            else:
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
                            field_type = old_value._meta.get_field(parts[-1])
                        except FieldDoesNotExist:
                            field_type = None
                        try:
                            value = getattr(old_value, f'get_{parts[-1]}_display')
                        except AttributeError:
                            pass
                    if not hasattr(value, 'through') and callable(value):
                        value = value()

                    if label is None:
                        label = self.label_from_field(field=field, field_type=field_type)
        return value, label, field_type

    def _add_many_to_many_field(self, label, query, query_filter=None, m2m_field=None,
                                html_barge=None, default='N/A', html_override=None,
                                entry_css_class=None, css_class=None, menu=None,
                                default_if=None, value_type=None, row_style=None, **kwargs):
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
                html += html_barge.replace('%1%', str(value))
            else:
                if hasattr(result, m2m_field):
                    value = getattr(result, m2m_field)
                    if callable(value):
                        value = value()
                    html += html_barge.replace('%1%', str(value))
                
        return self._add_entry_internal(label=label,
                                        value=html,
                                        default=default,
                                        html_override=html_override,
                                        entry_css_class=entry_css_class,
                                        css_class=css_class,
                                        menu=menu,
                                        default_if=default_if,
                                        value_type=value_type,
                                        row_style=row_style,
                                        **kwargs)

    def _add_entry_internal(self, value=None, field=None, label=None, default='N/A', link=None,
                            hidden=False, hidden_if_blank_or_none=None, html_override=None,
                            value_method=None, value_type=None,
                            entry_css_class=None, css_class=None, menu=None, default_if=None, row_style=None,
                            **kwargs):

        value, label, field_type = self.get_field_value(value=value, field=field, label=label)

        if hidden_if_blank_or_none is None:
            hidden_if_blank_or_none = self.hidden_if_blank_or_none

        if hidden or (hidden_if_blank_or_none and (value is None or value == '')):
            return None
        if isinstance(value, bool):
            return self.add_boolean_entry(value=value,
                                          label=label,
                                          hidden=hidden,
                                          html_override=html_override,
                                          entry_css_class=entry_css_class,
                                          css_class=entry_css_class,
                                          menu=menu,
                                          default_if=default_if,
                                          value_type=value_type,
                                          row_style=row_style,
                                          **kwargs)
        elif isinstance(value, datetime.date):
            return self.add_date_entry(value=value,
                                       label=label,
                                       hidden=hidden,
                                       html_override=html_override,
                                       menu=menu,
                                       default_if=default_if,
                                       value_type=value_type,
                                       row_style=row_style,
                                       **kwargs)
        elif hasattr(value, 'through'):
            return self._add_many_to_many_field(label=label,
                                                query=value,
                                                default=default,
                                                html_override=html_override,
                                                entry_css_class=entry_css_class,
                                                css_class=entry_css_class,
                                                menu=menu,
                                                default_if=default_if,
                                                value_type=value_type,
                                                row_style=row_style,
                                                **kwargs)
        else:
            if value is None or value == '' or default_if:
                value = default
                is_default = True
            else:
                is_default = False
            multiple_parts = isinstance(value, (list, tuple))

            if value_method is not None:
                if multiple_parts:
                    value = [value_method(v) for v in value]
                else:
                    value = value_method(value)
            if value_type is not None or field_type is not None:
                if multiple_parts:
                    if isinstance(field_type, (list, tuple)):
                        value = [self.get_value_from_type(v, value_type, ft, is_default, **kwargs)
                                 for v, ft in zip(value, field_type)]
                    else:
                        value = [self.get_value_from_type(v, value_type, field_type,
                                                          is_default, **kwargs) for v in value]
                else:
                    value = self.get_value_from_type(value, value_type, field_type, is_default, **kwargs)
            if html_override is not None:
                if multiple_parts:
                    value = [html_override.replace('%1%', str(v)) for v in value]
                else:
                    value = html_override.replace('%1%', str(value))

            if multiple_parts and kwargs.get('merge', False):
                merge_string = kwargs.get('merge_string', ' ')
                multiple_parts = False
                value = merge_string.join(['' if x is None else str(x) for x in value])

            if menu is not None and isinstance(menu, (list, tuple)):
                menu = HtmlMenu(self.request, self.button_menu_type).add_items(*menu)
            row_style_html = None
            if (row_style is not None and row_style in self._row_styles) or self._default_row_styles is not None:

                if row_style is not None:
                    html_row_style = self._row_styles[row_style]
                else:
                    html_row_style = self._row_styles[self._default_row_styles]

                value_dict = {'value': value,
                              'label': label,
                              'link': link,
                              **kwargs}
                if menu is not None:
                    value_dict['menu'] = menu.render()
                row_style_html = html_row_style.format_map(defaultdict(lambda: '', value_dict))

            entry = {'label': label,
                     'html': value,
                     'entry_css_class': entry_css_class,
                     'css_class': css_class,
                     'multiple_lines': multiple_parts,
                     'link': link,
                     'menu': menu,
                     'row_style_html': row_style_html,
                     **kwargs}
            return entry

    def get_value_from_type(self, value, value_type, field_type, is_default, **kwargs):
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
            if self.extra_card_info['setup_table'] is not None:
                field_setup_table_field = f'setup_table_{self.extra_card_info["setup_table"]}'
                if hasattr(self.view, field_setup_table_field):
                    setup_table_field = field_setup_table_field
            elif self.code is not None:
                field_setup_table_field = f'setup_table_{self.code}'
                if hasattr(self.view, field_setup_table_field):
                    setup_table_field = field_setup_table_field

            getattr(self.view, setup_table_field)(details_object=self.details_object, table=table)
            if hasattr(self.view, 'tables'):
                self.view.tables[self.code] = table
        elif self.group_type == CARD_TYPE_STANDARD and self.call_details_data:
            if self.code is not None and hasattr(self.view, f'get_{self.code}_data'):
                getattr(self.view, f'get_{self.code}_data')(card=self, details_object=self.details_object)
            elif hasattr(self.view, 'get_details_data'):
                getattr(self.view, 'get_details_data')(card=self, details_object=self.details_object)

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
            if current_sort.get(s[1]) != s[0]:
                o = self.extra_card_info['datatable_model'].objects.get(id=s[1])
                setattr(o, order_field, s[0])
                o.save()

    @staticmethod
    def label_from_field(field, field_type):
        if field_type is not None and hasattr(field_type, 'verbose_name') and field_type.verbose_name is not None:
            return field_type.verbose_name.capitalize()
        elif type(field) == str and len(field) > 0:
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

    def add_rows(self, *args, default='N/A', hidden=False, extra_row_kwargs=None):
        if extra_row_kwargs is None:
            extra_row_kwargs = {}
        for arg in args:
            if isinstance(arg, str):
                self.add_entry(field=arg, default=default, hidden=hidden, **extra_row_kwargs)
            elif isinstance(arg, dict):
                if 'default' not in arg:
                    arg['default'] = default
                if 'hidden' not in arg:
                    arg['hidden'] = hidden
                self.add_entry(**arg, **extra_row_kwargs)
            elif isinstance(arg, (list, tuple)):
                self.add_row(*arg)

    def render(self, override_card_context=None):
        extra_card_context = self.extra_card_context
        context = {'card': self,
                   'request': self.request,
                   'card_types': {'standard': CARD_TYPE_STANDARD,
                                  'datatable': CARD_TYPE_DATATABLE,
                                  'ordered_datatable': CARD_TYPE_ORDERED_DATATABLE,
                                  'html': CARD_TYPE_HTML}}

        if extra_card_context is not None:
            context = {**context, **extra_card_context}
        if override_card_context is not None:
            context = {**context, **override_card_context}

        template_name = self.template_name
        if template_name is None:
            template_name = self.template_defaults.get(self.group_type)

        if template_name in self.templates:
            template = self.templates[template_name]['name']
            if 'context' in self.templates[template_name]:
                context = {**self.templates[template_name]['context'], **context}
        else:
            template = template_name

        data = render_to_string(template, context)
        return mark_safe(data)

    def add_child_card_group(self, *args, div_css_class='', div_inner_css_class='',
                             div_inner_css='', override_card_context=None):
        if self.group_type not in [CARD_TYPE_CARD_GROUP, CARD_TYPE_CARD_LAYOUT]:
            raise Exception('This will only work for card group')
        self.child_card_groups.append({'div_css_class': div_css_class,
                                       'div_inner_css_class': div_inner_css_class,
                                       'div_inner_css': div_inner_css,
                                       'cards': args,
                                       'override_card_context': override_card_context})
