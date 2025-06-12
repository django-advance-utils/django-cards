import json

from ajax_helpers.utils import is_ajax
from django.http import HttpResponse
from django.template.loader import render_to_string

from cards.base import CardBase, CARD_TYPE_HTML, CARD_TYPE_CARD_LAYOUT, CARD_TYPE_STANDARD


class CardPostError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

    def value(self):
        return self.value


class CardMixin:
    """
    CardMixin provides reusable support for managing, rendering, and interacting with cards within a Django view.

    This mixin enables views to define and organize visual card components, including:
      - Detail cards displaying field values from Django models
      - HTML content blocks or templates
      - Lists and layout cards with nested groups
      - Datatables (including sortable tables with drag-and-drop)

    It supports both HTMX-style and traditional rendering and can be extended alongside other mixins such as `AjaxHelpers`.

    Features:
    ---------
    - Declarative card setup via `add_card()`, `add_html_card()`, and `add_list_card()`
    - Grouping via `add_card_group()` and nested layouts via `add_layout_card()`
    - Dynamic rendering using `get_context_data()` and `render_card_groups()`
    - Server-side datatable support with automatic setup, sorting, and row editing
    - Delegated card rendering via a configurable `card_cls` (default: `CardBase`)

    Expected Usage:
    ---------------
    Views using this mixin typically implement `setup_cards()` and optionally `setup_datatable_cards()` to declare cards.
    Cards can then be rendered into templates via `get_context_data()` or returned via AJAX responses.

    Example:
        class MyDetailView(CardMixin, DetailView):
            def setup_cards(self):
                self.add_card(title='Customer Info', details_object=self.object)
                self.add_html_card('custom_panel.html', {'customer': self.object})

    Requirements:
    -------------
    - The `card_cls` must implement a compatible interface (typically `CardBase`)
    - Works best in views where `self.request`, `self.object`, and `self.view` are available
    - Designed to integrate cleanly with `django-datatables`, `ajax-helpers`, and `django-menus`

    """
    card_cls = CardBase

    def __init__(self, *args, **kwargs):
        self.tables = {}
        self.cards = {}
        self.card_groups = {}
        super().__init__(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.POST.get('datatable_data'):
            table_id = request.POST['table_id']

            field_setup_table_field = f'setup_table_{table_id}'
            if hasattr(self, field_setup_table_field):
                self.setup_datatable_cards()
                table = self.tables[table_id]
                field_query = f'get_{table_id}_query'
                if hasattr(self, field_query):
                    results = getattr(self, field_query)(table, **kwargs)
                else:
                    results = table.get_query(**kwargs)
                table_data = table.get_json(request, results)
                return HttpResponse(table_data, content_type='application/json')
        # noinspection PyUnresolvedReferences
        if hasattr(super(), 'post'):
            # noinspection PyUnresolvedReferences
            return super().post(request, *args, **kwargs)
        elif is_ajax(request) and request.content_type == 'application/json':
            response = json.loads(request.body)
            raise CardPostError(f'May need to use AjaxHelpers Mixin or'
                                f' add one of these \n{", ".join(response.keys())}\nto ajax_commands ')

    def add_card_group(self, *args, div_css_class='', div_css='', error_if_not_found=True, group_code='main'):
        """
        Groups multiple cards together under a specified `group_code`, with optional CSS styling.

        Each argument in `*args` can be:
          - A string referencing a key in `self.cards`, or
          - A card object returned from `add_card()` or similar.

        This allows logical grouping and layout of related cards, e.g., in columns or sections of a page.

        Args:
            *args: A variable number of card name strings or card objects to include in the group.
            div_css_class (str, optional): CSS class to apply to the container div of this group. Defaults to an empty string.
            div_css (str, optional): Inline CSS styles to apply to the container div. Defaults to an empty string.
            error_if_not_found (bool, optional): If True, raises an error when a named card is not found in `self.cards`.
                                                 If False, missing cards are silently skipped. Defaults to True.
            group_code (str, optional): A string identifying which card group to append to (e.g., 'main', 'sidebar'). Defaults to 'main'.

        Side Effects:
            - Appends a dictionary to `self.card_groups[group_code]` containing:
                {
                    'div_css_class': div_css_class,
                    'div_css': div_css,
                    'cards': resolved_card_objects
                }

        Example:
            self.add_card_group(
                'welcome', 'split', 'table_multiple_columns',
                'other', 'person', 'multi_fields_example', collapsed_card,
                div_css_class='col-6 float-left',
            )
        """
        cards = []
        for card in args:
            if isinstance(card, str):
                if error_if_not_found or card in self.cards:
                    cards.append(self.cards[card])
            else:
                cards.append(card)

        if group_code not in self.card_groups:
            self.card_groups[group_code] = []

        self.card_groups[group_code].append({'div_css_class': div_css_class,
                                             'div_css': div_css,
                                             'cards': cards})

    def add_card(self,
                 card_name=None,
                 details_object=None,
                 title=None,
                 menu=None,
                 tab_menu=None,
                 template_name=None,
                 call_details_data=False,
                 group_type=CARD_TYPE_STANDARD,
                 show_created_modified_dates=False,
                 footer=None,
                 extra_card_context=None,
                 is_empty=False,
                 empty_template_name=None,
                 empty_message='N/A',
                 collapsed=None,
                 hidden_if_blank_or_none=None,
                 hidden_if_zero=None,
                 **kwargs):
        """
        Creates and adds a detail card to the view, using the configured card class.

        This method instantiates a new card (typically a UI component representing an object’s details),
        optionally keyed by `card_name`, and adds it to the `self.cards` dictionary for later use in rendering.

        Args:
            card_name (str, optional): A unique identifier for the card. Used as a dictionary key in `self.cards`.
            details_object (object, optional): The object containing data to be displayed. Defaults to `self.object` if not provided.
            title (str, optional): Title text shown on the card.
            menu (list, optional): A list of menu actions associated with the card.
            tab_menu (list, optional): A list of tabbed menu items for the card.
            template_name (str, optional): The template path to use for rendering the card.
            call_details_data (bool, optional): Whether to invoke a method to populate additional card data. Defaults to False.
            group_type (str, optional): Type or layout category for the card. Defaults to CARD_TYPE_STANDARD.
            show_created_modified_dates (bool, optional): Whether to include created/modified timestamps. Defaults to False.
            footer (str, optional): Footer content to render at the bottom of the card.
            extra_card_context (dict, optional): Additional context to pass to the template rendering.
            is_empty (bool, optional): Whether the card should render as an "empty state". Defaults to False.
            empty_template_name (str, optional): Template to render when the card is empty.
            empty_message (str, optional): Message to show when no data is available. Defaults to 'N/A'.
            collapsed (bool, optional): If True, the card is initially collapsed.
            hidden_if_blank_or_none (list, optional): Field names to hide if blank or None.
            hidden_if_zero (list, optional): Field names to hide if value is zero.
            **kwargs: Additional keyword arguments forwarded to the card constructor.

        Returns:
            object: The instantiated card object.

        Side Effects:
            - Stores the card in `self.cards` under `card_name` if `card_name` is provided.
        """


        request = getattr(self, 'request', None)

        if details_object is None:
            details_object = getattr(self, 'object', None)

        card = self.card_cls(request=request,
                             view=self,
                             details_object=details_object,
                             code=card_name,
                             title=title,
                             menu=menu,
                             tab_menu=tab_menu,
                             template_name=template_name,
                             call_details_data=call_details_data,
                             group_type=group_type,
                             show_created_modified_dates=show_created_modified_dates,
                             footer=footer,
                             extra_card_context=extra_card_context,
                             is_empty=is_empty,
                             empty_template_name=empty_template_name,
                             empty_message=empty_message,
                             collapsed=collapsed,
                             hidden_if_blank_or_none=hidden_if_blank_or_none,
                             hidden_if_zero=hidden_if_zero,
                             **kwargs)

        if card_name is not None:
            self.cards[card_name] = card
        return card

    def add_layout_card(self, card_name=None):
        """
        Creates and adds a layout card, which serves as a container for grouping and positioning child cards.

        A layout card allows other cards to be nested inside it using `add_child_card_group`, enabling flexible
        layout arrangements such as multi-column or grid-based designs.

        Args:
            card_name (str, optional): An optional identifier for the layout card. Used as a key in `self.cards` if provided.

        Returns:
            object: The instantiated layout card object, typically supporting `add_child_card_group()`.

        Example:
            layout_card = self.add_layout_card()

            layout_card.add_child_card_group(
                child_1_card,
                div_css_class='col-6 float-left',
                div_inner_css='border-style: solid;border-color: red',
                override_card_context={'item_css': 'color: blue'}
            )

            layout_card.add_child_card_group(
                child_2_card,
                div_css_class='col-6 float-left'
            )

            return layout_card
        """
        return self.add_card(card_name=card_name,
                             group_type=CARD_TYPE_CARD_LAYOUT)


    def add_list_card(self, list_entries, card_name=None, list_title='Entries',
                      selected_id='', list_menu=None, list_template_name='list_selection',
                      empty_list_message='No entries setup yet!',
                      extra_card_context=None):
        """
        Creates and adds a list-style card to the view, useful for displaying selectable or informative lists.

        This method wraps a list of entries into a card using the specified template and context, and delegates
        rendering to `add_card`.

        Args:
           list_entries (iterable): The list of entries to display (e.g., objects, dicts, or strings).
           card_name (str, optional): A unique identifier for the card. Used as a dictionary key in `self.cards`.
           list_title (str, optional): The title displayed at the top of the list card. Defaults to 'Entries'.
           selected_id (str, optional): The identifier of the currently selected list entry, if applicable.
           list_menu (list, optional): A list of menu items or actions related to the list.
           list_template_name (str, optional): The name of the template used to render the list. Defaults to 'list_selection'.
           empty_list_message (str, optional): Message shown if `list_entries` is empty. Defaults to 'No entries setup yet!'.
           extra_card_context (dict, optional): Additional context variables passed to the template.

        Returns:
           object: The instantiated list-style card object.
"""

        context = {'list_title': list_title,
                   'entries': list_entries,
                   'selected_id': selected_id,
                   'empty_list_message': empty_list_message,
                   'details_button_action_name': 'details_html',
                   'details_empty_button_action_name': 'empty_details_html'}
        if extra_card_context is not None:
            context.update(extra_card_context)

        card = self.add_card(card_name=card_name,
                             title=list_title,
                             menu=list_menu,
                             group_type=CARD_TYPE_HTML,
                             template_name=list_template_name,
                             extra_card_context=context)
        return card

    def get_context_data(self, **kwargs):
        """
        Constructs the context data for rendering the view, including cards and card groups.

        Returns:
            dict: Context dictionary containing rendered cards and grouped card blocks.
        """
        self.setup_datatable_cards()
        self.setup_cards()
        super_context = getattr(super(), 'get_context_data')
        if super_context and callable(super_context):
            context = super_context(**kwargs)
        else:
            context = {}
        context['cards'] = self.cards
        rendered_card_groups = {}
        for code, card_groups in self.card_groups.items():
            if len(card_groups) > 0:
                rendered_card_groups[code] = self.render_card_groups(card_groups)

        context['card_groups'] = rendered_card_groups
        return context

    def render_card_groups(self, card_groups):
        """
       Renders a collection of grouped cards into HTML using the default group template.

       Args:
           card_groups (list): List of card group dictionaries containing layout and card info.

       Returns:
           str: Rendered HTML string.
       """

        return render_to_string('cards/groups/groups.html', context={'groups': card_groups})

    def setup_cards(self):
        """
        Hook method for defining cards.

        Intended to be overridden in a subclass to add or configure cards for the view.
        Automatically called by `get_context_data()` before rendering cards.
        """
        if hasattr(super(), 'setup_cards'):
            super().setup_cards()

    def setup_datatable_cards(self):
        """
        Hook method for defining datatable-backed cards.

        Intended to be overridden in a subclass to setup any cards that use datatables.
        Automatically called before rendering or interacting with datatables.
        """
        if hasattr(super(), 'setup_datatable_cards'):
            super().setup_datatable_cards()

    def add_html_card(self, context_template_name, context=None, is_empty=False, **kwargs):
        """
        Renders a template into raw HTML and adds it as an HTML-style card to the view.

        This method uses Django's `render_to_string` to generate the card content from a template,
        then delegates card creation to `add_card` with `group_type=CARD_TYPE_HTML`.

        Args:
            context_template_name (str): The name or path of the template to render.
            context (dict, optional): Context data for rendering the template. If `details_object` is in `kwargs`,
                                      it is added to the context as `object`. The request is also added if available.
            is_empty (bool, optional): If True, no HTML is rendered and the card is treated as empty. Defaults to False.
            **kwargs: Additional keyword arguments passed to `add_card`, such as `card_name`, `title`, or `details_object`.

        Returns:
            object: The instantiated HTML-style card object.
        """
        if not is_empty:
            if context is None:
                context = {}
            if 'details_object' in kwargs:
                context['object'] = kwargs['details_object']
            if hasattr(self, 'request'):
                context['request'] = self.request
            html = render_to_string(context_template_name, context)
        else:
            html = ''

        return self.add_card(group_type=CARD_TYPE_HTML, html=html, is_empty=is_empty, **kwargs)

    def add_html_data_card(self, html, is_empty=False, **kwargs):
        """
        Adds a pre-rendered HTML block as an HTML-style card to the view.

        If `html` is a renderable object (e.g., a Django `TemplateResponse` or similar), it will be rendered into a string.
        If `is_empty` is True or `html` is None, an empty card will be rendered instead.

        Args:
            html (str or renderable, optional): The HTML content or an object with a `.render()` method.
            is_empty (bool, optional): If True, the card is considered empty and no HTML will be shown. Defaults to False.
            **kwargs: Additional keyword arguments passed to `add_card`, such as `card_name`, `title`, or `footer`.

        Returns:
            object: The instantiated HTML-style card object.
        """
        if not is_empty and html is not None:
            if not isinstance(html, str) and hasattr(html, 'render'):
                html = html.render()
        else:
            html = ''
        return self.add_card(group_type=CARD_TYPE_HTML, html=html, is_empty=is_empty, **kwargs)


    def row_edit(self, **kwargs):
        """
        Updates a single row in a datatable with edited values received via AJAX.

        Looks up the row by ID, applies the changes using the appropriate column's alter logic,
        and returns the refreshed row HTML.

        Args:
           **kwargs: Must include 'row_data', 'table_id', 'row_no', and 'changed' field index.

        Returns:
           str: Rendered HTML for the updated row.
        """
        row_data = json.loads(kwargs.pop('row_data'))
        self.setup_datatable_cards()
        table_id = kwargs['table_id']
        table = self.tables[table_id]
        row_object = table.model.objects.get(pk=kwargs['row_no'][1:])
        field_setup_table_field = f'setup_table_{table_id}'
        if hasattr(self, field_setup_table_field):
            getattr(self, field_setup_table_field)(table=table, details_object=self.cards[table_id].details_object)
        table.columns[kwargs['changed'][0]].alter_object(row_object, row_data[kwargs['changed'][0]])
        return table.refresh_row(self.request, kwargs['row_no'])

    def datatable_sort(self, **kwargs):
        self.setup_datatable_cards()
        card = self.cards.get(kwargs.get('table_id', ''))
        card.datatable_sort(**kwargs)

        return self.command_response('null')
