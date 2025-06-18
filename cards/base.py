import datetime
import json
from collections import defaultdict

from ajax_helpers.utils import random_string
from django.core.exceptions import FieldDoesNotExist
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.text import slugify
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
    """
    Card Framework for Django Views

    This module defines the `CardBase` class and associated constants used to render
    dynamic, configurable card-style UI components within Django views. Cards are modular
    HTML blocks that support various types of content presentation, such as:

    - Object detail fields (label/value pairs)
    - Data tables (including sortable and reorderable variants)
    - HTML fragments
    - Selectable lists
    - Grouped or nested card layouts

    Each card type supports advanced features such as:
    - Custom row styles and templates
    - Bootstrap-compatible layout options
    - Action button menus and tabbed interfaces
    - Auto-fetching of model field values with display formatting
    - Integration with django-datatables and django-menus

    Card rendering is customizable via Django templates and context injection,
    enabling easy reuse across views for admin dashboards, detail views, and inspectors.

    Common use cases include:
    - Object inspectors in a detail view
    - Nested layout containers in dashboards
    - Scrollable list selections with detail-on-click
    - Tabbed or collapsible card groups

    Main Classes:
        - `CardBase`: Core card logic for managing structure, rendering, and content population.

    Constants:
        - `CARD_TYPE_STANDARD`: Standard label/value detail card
        - `CARD_TYPE_DATATABLE`: Embedded datatable
        - `CARD_TYPE_ORDERED_DATATABLE`: Datatable with drag-and-drop ordering
        - `CARD_TYPE_HTML`: Arbitrary HTML card
        - `CARD_TYPE_LIST_SELECTION`: Scrollable list of items (click to trigger detail)
        - `CARD_TYPE_CARD_GROUP`: Group of cards rendered together
        - `CARD_TYPE_CARD_LAYOUT`: Nested layout container for arranging child card groups

    Intended to be used in combination with views that inherit from `CardList`, `CardTree`, or
    custom mixins providing card construction logic.

    """
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
                                                'enable_reorder': False,
                                                'modal': False}},
                 'list_selection_reorder': {'name': 'cards/standard/list_selection.html',
                                          'context': {'card_css_class': 'card django-card',
                                                      'card_link_css_class': 'list-group-item cards-list-group-item',
                                                      'card_body_css_class': 'overflow-auto',
                                                      'card_body_css_style': 'height: calc(100vh - 150px);',
                                                      'enable_reorder': True,
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
                 collapsed=None, hidden_if_blank_or_none=None, hidden_if_zero=None, **kwargs):
        """
        Initializes a card instance used to render a block of content within a view.

        Cards are modular UI components that can display object details, tables, lists, HTML,
        or even act as layout containers for grouping and positioning other cards.

        Args:
            request (HttpRequest): The current request object, used for context resolution.
            code (str, optional): A unique identifier for the card (used as a lookup key).
            view (View, optional): The parent view instance that is generating the card.
            details_object (object, optional): The main data object to be displayed in the card.
            title (str, optional): The heading/title displayed on the card.
            menu (list, optional): Optional list of action menu items for the card.
            tab_menu (list, optional): Optional tab menu items for the card.
            template_name (str, optional): Template to be used for rendering the card.
            call_details_data (bool, optional): Whether to invoke a method to populate dynamic data. Defaults to False.
            group_type (int, optional): Defines the visual and functional type of the card. Defaults to CARD_TYPE_STANDARD.
                Valid values include:
                    - CARD_TYPE_STANDARD (1): Default detail-style card
                    - CARD_TYPE_DATATABLE (2): A card containing a data table
                    - CARD_TYPE_ORDERED_DATATABLE (3): A card with a sortable/ordered table
                    - CARD_TYPE_HTML (4): A card with raw or rendered HTML content
                    - CARD_TYPE_LIST_SELECTION (5): A card showing a selectable list of entries
                    - CARD_TYPE_CARD_GROUP (6): A logical grouping of cards (e.g. tabbed or side-by-side)
                    - CARD_TYPE_CARD_LAYOUT (7): A container card that can hold child card groups
            show_created_modified_dates (bool, optional): If True, adds created/modified timestamps to the card. Defaults to False.
            footer (str, optional): Optional footer content to display at the bottom of the card.
            extra_card_context (dict, optional): Extra context passed to the card template.
            is_empty (bool, optional): Whether the card should be considered empty (e.g. for fallback rendering). Defaults to False.
            empty_template_name (str, optional): Template to use if the card is empty.
            empty_message (str, optional): Message to display when the card has no data. Defaults to 'N/A'.
            collapsed (bool, optional): If True, the card is initially collapsed.
            hidden_if_blank_or_none (list, optional): Field names to hide if their values are blank or None.
            hidden_if_zero (list, optional): Field names to hide if their values are zero.
            **kwargs: Additional keyword arguments for custom behavior or extension.

        Notes:
            - Layout cards (CARD_TYPE_CARD_LAYOUT) support nesting of other cards via `add_child_card_group()`.
        """

        if code is None:
            if title is not None:
                code = slugify(title).replace('-', '_') + '_card'
            else:
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
        self.hidden_if_zero = hidden_if_zero

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
    def add_extra_card_info(self, extra_info, group_type, **kwargs):
        """
        Adds additional context or configuration to a card's extra info dictionary based on its group type.

        This method enriches the `extra_info` dictionary with data relevant to specific card types such as
        data tables or HTML blocks.

        Args:
            extra_info (dict): The dictionary to which extra card information will be added.
            group_type (int): The card type, used to determine what extra information is added.
                Supported values:
                    - CARD_TYPE_DATATABLE
                    - CARD_TYPE_ORDERED_DATATABLE
                    - CARD_TYPE_HTML
            **kwargs: Additional keyword arguments that provide data relevant to the given group type.
                - For data table cards:
                    - datatable_id (str): ID for the datatable (defaults to the card's code).
                    - datatable (object): The datatable instance or configuration.
                    - datatable_model (Model): The model backing the datatable, if any.
                    - setup_table (callable): A callable used to set up the datatable.
                    - order_field (str): Ordering field name for ordered datatables (defaults to 'order').
                - For HTML cards:
                    - html (str): The raw HTML content to render.

        Side Effects:
            - Mutates `extra_info` in-place by adding the appropriate keys for the given card type.
        """
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
        """
        Adds a boolean-style entry to the card, rendered as a green checkmark or red cross icon.

        This method is typically not called directly. It is invoked internally by `add_entry` either:
          - when `value_type='boolean'` is explicitly set, or
          - when the value is detected to be a boolean via `isinstance(value, bool)`.

        Args:
            value (bool): The boolean value to display. Renders a green check icon if True, red cross if False.
            label (str, optional): The label to display alongside the icon.
            hidden (bool, optional): If True, the entry is not shown.
            html_override (str or HtmlElement, optional): Custom HTML override for full value rendering.
            entry_css_class (str, optional): CSS class for the value/content area.
            css_class (str, optional): CSS class for the row container.
            menu (list, optional): Optional action menu items for the entry.
            default_if (callable, optional): Optional function to determine if default text should be used.
            value_type (str, optional): Rendering hint (usually 'boolean') passed from higher-level `add_entry`.
            row_style (str, optional): Named row style for custom layout, if defined.
            **kwargs: Additional keyword arguments for rendering or substitution in styled rows.

        Returns:
            dict: A dictionary representing the entry, suitable for appending to a card row.

        Example:
            # Usually called indirectly via add_entry:
            card.add_entry(label='Is Active?', value=True)
            card.add_entry(label='Confirmed', value=False, value_type='boolean')
            """
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
        """
        Adds a date-style entry to the card, formatted as 'dd/mm/yy'.

        This method is normally called internally by `add_entry`, either:
          - when `value_type='date'` is explicitly provided, or
          - when the value is identified as a `datetime.date` instance via `isinstance`.

        Args:
            value (datetime.date or datetime.datetime): The date to display.
            label (str, optional): Label to display alongside the date.
            hidden (bool, optional): If True, the entry is not shown.
            html_override (str or HtmlElement, optional): Custom HTML to override the value display.
            entry_css_class (str, optional): CSS class for the value/content span or div.
            css_class (str, optional): CSS class for the row container.
            menu (list, optional): Optional list of menu items or actions for this entry.
            default_if (callable, optional): Function to determine if the default should be shown.
            value_type (str, optional): Rendering hint (e.g., 'date') passed from `add_entry`.
            row_style (str, optional): Optional row style to apply to this entry.
            **kwargs: Additional arguments for layout, styling, or context substitution.

        Returns:
            dict: The generated entry dictionary, suitable for inclusion in a card row.

        Example:
            # Typically called via add_entry:
            card.add_entry(label='Created On', value=obj.created)
            card.add_entry(label='Expires', value=date(2024, 12, 31), value_type='date')
        """
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
        """
        Adds a row to the card, containing one or more field entries.

        Each argument can be:
          - A string: treated as a field name (auto-fetched from `details_object`).
          - A dict: passed as keyword arguments to `_add_entry_internal()`.

        The method supports both single-entry and multi-entry rows:
          - If only one entry is provided, a standard row is added.
          - If multiple entries are provided, the row is styled using Bootstrap column classes
            (`col-sm-6`, `col-sm-4`, etc.) unless explicitly overridden via `entry_css_class`.

        Args:
            *args: Field names or entry definition dictionaries.
            extra_row_kwargs (dict, optional): Additional keyword arguments applied to each entry.

        Side Effects:
            - Appends a structured row dictionary to `self.rows`.

        Example:
            card.add_row('first_name', 'last_name')

            card.add_row(
                {'field': 'email', 'label': 'Email Address'},
                {'field': 'phone', 'label': 'Phone Number'},
                extra_row_kwargs={'css_class': 'text-muted'}
            )
        """
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
                  default='N/A', link=None, hidden=False, hidden_if_blank_or_none=None, hidden_if_zero=None,
                  html_override=None, value_method=None, value_type=None, default_if=None, row_style=None, **kwargs):
        """
        Adds a single entry (label/value pair) to the card as a new row.

        Entries can be simple strings, resolved fields from an object, or complex structures using a named
        `row_style` with HTML elements for fine-grained layout.

        Args:
            value (any, optional): The value to display. Can be a string, number, dict (for `row_style`), or None.
            field (str, optional): Field name to auto-fetch value from `details_object` if `value` is not provided.
            label (str, optional): Label to display alongside the value.
            entry_css_class (str, optional): CSS class for the value span/div.
            css_class (str, optional): CSS class for the row container.
            default (str, optional): Default text to display if the value is None or empty. Defaults to 'N/A'.
            link (str or callable, optional): URL or link generator for making the value a hyperlink.
            hidden (bool, optional): If True, the entry is not shown.
            hidden_if_blank_or_none (bool, optional): If True, hides the entry if the value is blank or None.
            hidden_if_zero (bool, optional): If True, hides the entry if the value is 0.
            html_override (str or HtmlElement, optional): Custom HTML content that overrides the entire value cell.
            value_method (str or callable, optional): A method or method name to compute the value dynamically.
            value_type (str, optional): Optional rendering hint (e.g., 'currency', 'boolean', etc.).
            default_if (callable, optional): A function to conditionally apply the default.
            row_style (str, optional): A named layout style (defined via `add_row_style`) that replaces default rendering.
            **kwargs: Additional named parameters used for row style substitution or link construction.

        Side Effects:
            - Appends a new row containing this entry to `self.rows`.

        Example:
            card = self.add_card(title='Row Style Examples no DB')

            card.add_row_style('test', html=HtmlDiv([
                HtmlElement('span', contents=[HtmlElement('h4', contents='{label}')]),
                HtmlElement('span', contents='{value}')
            ]))

            card.add_entry(value='Row Style line', label='Styled Entry', row_style='test')

            card.add_entry(
                value={'v1': 'foo', 'v2': 'bar'},
                label='Multi-value',
                row_style='multi_value'
            )
        """

        entry = self._add_entry_internal(value=value,
                                         field=field,
                                         label=label,
                                         entry_css_class=entry_css_class,
                                         css_class=css_class,
                                         default=default,
                                         link=link,
                                         hidden=hidden,
                                         hidden_if_blank_or_none=hidden_if_blank_or_none,
                                         hidden_if_zero=hidden_if_zero,
                                         html_override=html_override,
                                         value_method=value_method,
                                         value_type=value_type,
                                         default_if=default_if,
                                         row_style=row_style,
                                         **kwargs)
        if entry is not None:
            self.rows.append({'type': 'standard', 'entries': [entry]})

    def add_html_entry(self, template_name, context=None, **kwargs):
        """
        Renders a template to HTML and adds it as a custom HTML row in the card.

        This method allows full control over the row layout using a Django template. Context variables
        from both `context` and `**kwargs` are merged and passed to the template.

        Args:
            template_name (str): The path to the Django template to render.
            context (dict, optional): Context dictionary to pass to the template.
            **kwargs: Additional context variables, and optional extra keys included in the final row dict.

        Side Effects:
            - Appends a row to `self.rows` with type `'html'` and rendered HTML content.

        Example:
            card.add_html_entry(
                template_name='cards/custom_row.html',
                context={'title': 'Custom Content'},
                css_class='my-custom-row'
            )
        """
        if context is None:
            context = {}
        context = {**context, **kwargs}
        html = render_to_string(template_name=template_name, context=context)
        self.rows.append({'type': 'html', 'html': html, **kwargs})

    def add_row_style(self, name, html, is_default=False):
        """
        Defines a named row style for custom rendering of card entries.

        A row style allows you to fully control the HTML layout of an entry by using placeholders such as
        `{label}`, `{value}`, or custom keys (e.g., `{test}`, `{value[v1]}`) that can be substituted at render time.

        Args:
            name (str): The name of the style, used to reference this layout in `add_entry(row_style=...)`.
            html (str or HtmlElement): A string of HTML or an HtmlElement object with placeholders for substitution.
            is_default (bool, optional): If True, this style becomes the default for all subsequent entries.

        Side Effects:
            - Registers the style in `self._row_styles` under the given `name`.
            - Optionally updates `self._default_row_styles` if `is_default` is True.

        Example:
            card = self.add_card(title='Row Style Example')

            card.add_row_style('test', html=HtmlDiv([
                HtmlElement('span', contents=[
                    HtmlElement('h4', contents='{label}')
                ]),
                HtmlElement('span', contents='{value}')
            ]))

            card.add_entry(label='Custom Row', value='Styled Entry', row_style='test')
        """
        if not isinstance(html, str) and hasattr(html, 'render'):
            html = html.render()
        self._row_styles[name] = html
        if is_default:
            self._default_row_styles = name

    def set_default_style(self, name=None):
        """
        Sets the default row style to be used for entries that do not explicitly specify one.

        Args:
            name (str, optional): The name of the row style to set as default. Must exist in `self._row_styles`.

        Side Effects:
            - Updates `self._default_row_styles` to the given style name if it exists.
        """
        if name in self._row_styles:
            self._default_row_styles = name

    def get_field_value(self, value, field, label):
        """
        Internal method to resolve a field value, label, and field type from a given object.

        This is primarily used by `add_entry()` and related methods when `field` is specified but `value` is not.
        It handles:
          - Field traversal via double-underscore paths (e.g. `user__email`)
          - Multi-field tuples/lists
          - Field display methods (e.g. `get_status_display`)
          - Django model field type extraction via `_meta.get_field()`
          - Label fallback using `label_from_field()`

        Args:
            value (any): A pre-resolved value (if already known). If None, will attempt to resolve from `field`.
            field (str or list/tuple of str): The field name or path to resolve from `self.details_object`.
            label (str or None): Optional label. If not provided, one will be generated from the field name.

        Returns:
            tuple:
                value (any): The resolved value (or list of values if `field` is a list/tuple).
                label (str or None): A label for display purposes.
                field_type (Field or list of Field or None): The Django model field type(s), if available.

        Notes:
            - Normally called internally by entry rendering logic.
            - Uses `getattr()` for dynamic resolution and supports method calls (e.g. display methods).
            - Handles missing attributes and non-field values gracefully.
        """
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
        """
        Internal method for rendering many-to-many or reverse-related objects as an HTML badge list.

        This method is normally called indirectly by `add_entry()` when the value is a Django `ManyToManyManager`
        or reverse relation (i.e. when `hasattr(value, 'through')` is True). It outputs a row displaying each related
        object as a styled badge.

        Args:
            label (str): The label to display for the row.
            query (QuerySet or RelatedManager): The related manager to query related objects.
            query_filter (dict, optional): Optional filter applied to the query results.
            m2m_field (str, optional): Name of an attribute or method on each related object to display. If not set,
                                       the related object is stringified.
            html_barge (str, optional): HTML snippet for wrapping each item (default is a Bootstrap badge).
                                        Use `%1%` as a placeholder for the rendered value.
            default (str, optional): Fallback text if the relation is empty. Defaults to `'N/A'`.
            html_override (str, optional): Full HTML override for the entire value cell.
            entry_css_class (str, optional): CSS class for the value cell.
            css_class (str, optional): CSS class for the row container.
            menu (list, optional): Optional action menu for the row.
            default_if (callable, optional): Callable to determine if the default should be applied.
            value_type (str, optional): Optional rendering hint (`'m2m'`).
            row_style (str, optional): Optional named row style for layout customization.
            **kwargs: Any additional arguments passed through to `_add_entry_internal()`.

        Returns:
            dict: An entry dictionary suitable for adding to the card's row structure.

        Example (automatic via add_entry):
            card.add_entry(
                label='Assigned Tags',
                value=obj.tags,  # a ManyToMany manager or reverse relation
                m2m_field='name',  # optional: field or method to display
                value_type='m2m'  # optional: explicitly mark this as a many-to-many value
            )
        """

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
                            hidden=False, hidden_if_blank_or_none=None, hidden_if_zero=None, html_override=None,
                            value_method=None, value_type=None,
                            entry_css_class=None, css_class=None, menu=None, default_if=None, row_style=None,
                            **kwargs):
        """
        Internal method for creating a fully-resolved entry dictionary used in card rows.

        This is the central rendering engine behind `add_entry()` and related helpers. It handles:
          - Value and label resolution from a field (via `get_field_value`)
          - Conditional hiding (empty, zero, or flagged as hidden)
          - Type-based dispatch to boolean, date, or many-to-many renderers
          - Formatting logic (custom value methods, HTML overrides, merging)
          - Custom row styling via defined `row_style` templates
          - Optional link and menu rendering

        Args:
            value (any, optional): Direct value to display. If None, `field` will be used to resolve it.
            field (str, optional): Field name/path to resolve from `details_object` if value is not given.
            label (str, optional): Label to show next to the value. If None, will be inferred from `field`.
            default (str, optional): Fallback value if the resolved value is None or empty. Defaults to 'N/A'.
            link (str or callable, optional): Optional link to wrap the value.
            hidden (bool, optional): If True, the entry is skipped entirely.
            hidden_if_blank_or_none (bool, optional): If True, hides the entry when value is None or empty.
            hidden_if_zero (bool, optional): If True, hides the entry when value is 0.
            html_override (str, optional): Template HTML to use instead of the value. Use `%1%` as placeholder.
            value_method (callable, optional): Function to transform the value before rendering.
            value_type (str, optional): Optional rendering hint (e.g., 'boolean', 'currency', 'm2m').
            entry_css_class (str, optional): CSS class for the value cell.
            css_class (str, optional): CSS class for the overall row container.
            menu (list, optional): A list of menu items (converted to `HtmlMenu` if present).
            default_if (callable, optional): Function to determine if the default value should be used.
            row_style (str, optional): Named row style to use for custom layout rendering.
            **kwargs: Additional arguments used for formatting, merging, or row style substitution.

        Returns:
            dict or None:
                A fully constructed entry dictionary if visible and valid; None if skipped due to visibility rules.

        Example (indirect):
            Called automatically by:
                - `add_entry()`
                - `add_row()`
                - `add_rows()`
                - Any value auto-dispatching logic

        Notes:
            - This method supports merging multiple values (e.g., list or tuple) into a single string using `merge=True`.
            - Row styles can be defined using `add_row_style()` and referenced by name here.
        """

        value, label, field_type = self.get_field_value(value=value, field=field, label=label)

        if hidden_if_blank_or_none is None:
            hidden_if_blank_or_none = self.hidden_if_blank_or_none

        if hidden_if_zero is None:
            hidden_if_zero = self.hidden_if_zero

        if hidden or (hidden_if_blank_or_none and (value is None or value == '') or
                      (hidden_if_zero and isinstance(value, (float, int)) and value == 0)):
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
        """
        Hook method for transforming a value based on its type before rendering.

        This method can be overridden in subclasses to apply formatting or conversions
        for specific `value_type`s or Django `field_type`s.

        Args:
            value (any): The raw value to transform.
            value_type (str): An explicit type hint (e.g., 'currency', 'percent', etc.).
            field_type (Field): The Django model field instance, if available.
            is_default (bool): Whether the value is a default fallback rather than real data.
            **kwargs: Additional context passed from the entry logic.

        Returns:
            any: The transformed value, or the original value by default.

        Example:
            def get_value_from_type(self, value, value_type, field_type, is_default, **kwargs):
                if value_type == 'currency':
                    return f"£{value:,.2f}"
                return super().get_value_from_type(value, value_type, field_type, is_default, **kwargs)
        """
        return value

    def process_data(self):
        """
        Internal method that populates card content depending on its group type.

        For datatable-type cards, this initializes the datatable (if not already set), attaches it
        to `self.extra_card_info`, and calls the appropriate `setup_table_*` method on the view.

        For standard cards with `call_details_data=True`, it attempts to call a view method to load
        additional content (e.g., `get_<code>_data()` or `get_details_data()`).

        Behavior:
            - CARD_TYPE_DATATABLE / CARD_TYPE_ORDERED_DATATABLE:
                - Initializes the table using `add_table()` or `add_ordered_table()`.
                - Attaches it to `self.extra_card_info['datatable']`.
                - Looks up a table setup method on the view:
                    * `setup_table_<custom>` (if `setup_table` key is set)
                    * `setup_table_<code>` (fallback if available)
                    * `setup_table` (default)
                - Adds the table to `view.tables[code]` if that dict exists.

            - CARD_TYPE_STANDARD:
                - If `call_details_data` is True:
                    * Tries to call `get_<code>_data(card, details_object)` if defined on the view.
                    * Otherwise falls back to `get_details_data(card, details_object)`.

        Side Effects:
            - Mutates `self.extra_card_info` and potentially `self.view.tables`.

        Notes:
            - This method is called internally, usually during rendering or card setup.
            - Assumes `self.view` has the required setup/data methods.
        """
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
        """
        Internal helper to create and attach a standard (non-orderable) datatable to the card.

        Args:
            model (Model): The Django model backing the table.
            table_id (str, optional): Optional identifier for the datatable instance.

        Returns:
            DatatableTable: The constructed datatable instance (with `ajax_data` set to False).

        Side Effects:
            - Sets `self.extra_card_info['datatable']` to the new table.
        """
        table = DatatableTable(table_id=table_id, model=model, view=self.view)
        self.extra_card_info['datatable'] = table
        table.ajax_data = False
        return table

    def add_ordered_table(self, model, order_field, table_id=None):
        """
        Internal helper to create and attach an ordered datatable with drag-and-drop support.

        Args:
            model (Model): The Django model to be rendered in the table.
            order_field (str): The field used to determine row ordering (e.g., 'order').
            table_id (str, optional): Optional identifier for the table.

        Returns:
            OrderedDatatable: The constructed ordered datatable with reorder plugin enabled.

        Side Effects:
            - Adds the `Reorder` plugin to the table.
            - Sets `self.extra_card_info['datatable']` to the new table.
            - Disables `ajax_data`.
        """
        table = OrderedDatatable(table_id=table_id,
                                 model=model,
                                 view=self.view,
                                 order_field=order_field)
        table.add_plugin(Reorder)
        table.ajax_data = False
        self.extra_card_info['datatable'] = table
        return table

    def get_created_modified_dates(self, details_object):
        """
        Returns the created and modified timestamps from the given object, if available and enabled.

        This method checks whether `show_created_modified_dates` is enabled and whether the
        `details_object` has `created` and `modified` attributes. If so, it returns them as a tuple.

        Args:
            details_object (object): The object from which to retrieve the `created` and `modified` timestamps.

        Returns:
            tuple[datetime, datetime] or None:
                A tuple containing (created, modified) if available; otherwise, None.
        """
        if (self.show_created_modified_dates and details_object and
                hasattr(details_object, 'created') and hasattr(details_object, 'modified')):
            return details_object.created, details_object.modified
        return None

    def datatable_sort(self, **kwargs):
        """
        Updates the order of rows in an ordered datatable based on a new sort sequence.

        This method is typically called after a "Move Up" / "Move Down" action in the UI,
        where the frontend sends a list of new positions for items in the table.

        Args:
            **kwargs:
                sort (list of tuples): A list of (new_order, object_id) pairs representing the updated order.

        Example:
            kwargs['sort'] = [
                (1, 42),  # Object with ID 42 should now be first
                (2, 37),  # Object with ID 37 should now be second
                ...
            ]

        Behavior:
            - Fetches current `order_field` values for the specified IDs.
            - Compares current values to the desired new order.
            - Updates and saves objects where the order has changed.

        Notes:
            - Requires `self.extra_card_info['order_field']` to be set (e.g. 'order').
            - `self.extra_card_info['datatable_model']` must be the model class for the table.
            - Minimizes writes by only updating rows where the order actually differs.
        """
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
        """
        Generates a human-readable label from a field name or type.

        This utility is typically used to auto-generate labels for fields when one is not explicitly provided.

        Args:
            field (str or any): The field name, usually a string. Can include slashes or double underscores.
            field_type (Field, optional): A Django model field or similar object. If it has a `verbose_name`,
                                          that is used as the label (capitalized).

        Returns:
            str: A human-readable label derived from the field name or verbose name.

        Examples:
            label_from_field("user__email", None)       # → "Email"
            label_from_field("created_at", None)        # → "Created At"
            label_from_field("camelCaseField", None)    # → "Camel Case Field"
        """
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
        """
        Adds multiple rows to the card in a flexible, declarative format.

        Each argument can be:
          - A string: treated as a field name (used to fetch from `details_object`).
          - A dict: passed as keyword arguments to `add_entry()`, with support for per-entry overrides.
          - A list or tuple: passed directly to `add_row()` for manual row construction.

        Common options like `default` and `hidden` are applied to all entries unless overridden.

        Args:
            *args: Variable-length list of fields, dicts, or (args) for `add_row()`.
            default (str, optional): Default value to display if no value is found. Defaults to 'N/A'.
            hidden (bool, optional): Whether to hide the entry/row if not overridden per-entry.
            extra_row_kwargs (dict, optional): Additional kwargs applied to each entry (unless overridden).

        Example:
            card.add_rows(
                'name',
                {'field': 'email', 'label': 'Email Address'},
                ('first_name', 'last_name'),  # calls add_row with multiple fields
                default='Not available',
                extra_row_kwargs={'entry_css_class': 'text-muted'}
            )
        """
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
        """
        Renders the card as an HTML string using the appropriate template and context.

        This method:
          - Builds the rendering context from:
              * `self` (the card instance)
              * `self.extra_card_context` (if provided)
              * `override_card_context` (if provided at render time)
          - Resolves the correct template to use:
              * If `self.template_name` is set, it uses that.
              * Otherwise, it falls back to `self.template_defaults[self.group_type]`.
              * If `self.templates[template_name]` exists, it may override both the template path and context.
          - Uses `render_to_string()` to produce the final HTML output.

        Args:
            override_card_context (dict, optional): Context values that override or extend the default card context.

        Returns:
            str: Safe HTML string rendered from the selected template.

        Notes:
            - Supports preloaded templates via `self.templates` dict, with optional custom context injection.
            - Includes a default `card_types` mapping in the context for conditional logic in templates.

        Example:
            html = card.render(override_card_context={'highlight': True})
        """
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
        """
        Adds a group of child cards to a layout- or group-style card.

        This method is only valid for cards with `group_type` set to `CARD_TYPE_CARD_GROUP` or `CARD_TYPE_CARD_LAYOUT`.
        It defines a logical grouping of cards for rendering within a layout card, with optional CSS classes
        and per-card context overrides.

        Args:
            *args: One or more card instances to include in the child group.
            div_css_class (str, optional): CSS class applied to the outer wrapper div of the group.
            div_inner_css_class (str, optional): CSS class applied to the inner wrapper div around the cards.
            div_inner_css (str, optional): Inline CSS styles for the inner wrapper div.
            override_card_context (dict, optional): Optional context overrides for each child card.

        Raises:
            Exception: If the card is not a layout- or group-type card.

        Side Effects:
            - Appends a dictionary to `self.child_card_groups` representing the child group configuration.

        Example:
            layout_card = self.add_layout_card()

            layout_card.add_child_card_group(
                child_1_card,
                div_css_class='col-6 float-left',
                div_inner_css='border-style: solid; border-color: red',
                override_card_context={'item_css': 'color: blue'}
            )

            layout_card.add_child_card_group(
                child_2_card,
                div_css_class='col-6 float-left'
            )
        """
        if self.group_type not in [CARD_TYPE_CARD_GROUP, CARD_TYPE_CARD_LAYOUT]:
            raise Exception('This will only work for card group')
        self.child_card_groups.append({'div_css_class': div_css_class,
                                       'div_inner_css_class': div_inner_css_class,
                                       'div_inner_css': div_inner_css,
                                       'cards': args,
                                       'override_card_context': override_card_context})
