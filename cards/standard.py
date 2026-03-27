import json

from ajax_helpers.utils import is_ajax
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string

from cards.base import CardBase, CARD_TYPE_HTML, CARD_TYPE_CARD_LAYOUT, CARD_TYPE_STANDARD, CARD_TYPE_CARD_MESSAGE, CARD_TYPE_LINKED_DATATABLES, CARD_TYPE_ACCORDION, CARD_TYPE_PANEL_LAYOUT, CARD_TYPE_IFRAME, CARD_TYPE_TREEGRID
from cards.panel_layout import PanelLayout, PanelSplit


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
                linked_filter_field = request.POST.get('linked_filter_field')
                linked_filter_value = request.POST.get('linked_filter_value')
                field_query = f'get_{table_id}_query'
                if hasattr(self, field_query):
                    results = getattr(self, field_query)(table, **kwargs)
                elif linked_filter_field and linked_filter_value:
                    table.filter[linked_filter_field] = linked_filter_value
                    results = table.get_query(**kwargs)
                else:
                    results = table.get_query(**kwargs)
                table_data = table.get_json(request, results)
                return HttpResponse(table_data, content_type='application/json')
        # Treegrid self-dispatch: treegrid_data + card_id in JSON body
        if is_ajax(request) and request.content_type == 'application/json':
            try:
                body = json.loads(request.body)
            except (json.JSONDecodeError, ValueError):
                body = {}
            if body.get('treegrid_data'):
                card_id = body.get('card_id', '')
                parent_key = body.get('parent')
                method_name = f'get_treegrid_{card_id}_data'
                if hasattr(self, method_name):
                    data = getattr(self, method_name)(parent=parent_key)
                    return JsonResponse(data, safe=False)
                return JsonResponse([], safe=False)
        # noinspection PyUnresolvedReferences
        if hasattr(super(), 'post'):
            # noinspection PyUnresolvedReferences
            return super().post(request, *args, **kwargs)
        elif is_ajax(request) and request.content_type == 'application/json':
            response = json.loads(request.body)
            raise CardPostError(f'May need to use AjaxHelpers Mixin or'
                                f' add one of these \n{", ".join(response.keys())}\nto ajax_commands ')

    def add_card_group(self, *args, div_css_class='', div_css='', div_id='', script='', group_title='', error_if_not_found=True, group_code='main'):
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
            script (str, optional): JavaScript code to render in a ``<script>`` tag after the group div. Defaults to an empty string.
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

        Examples:
            self.add_card_group(
                'welcome', 'split', 'table_multiple_columns',
                'other', 'person', 'multi_fields_example', collapsed_card,
                div_css_class='col-6 float-left',
            )

            # Attach a script to a card group
            self.add_card_group(
                'timeline',
                script='$(function(){ $(".tl-evt").on("click", function(){ alert("clicked"); }); })',
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
                                             'div_id': div_id,
                                             'script': script,
                                             'group_title': group_title,
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
                 show_header=True,
                 header_icon=None,
                 header_css_class='',
                 ajax_reload=False,
                 reload_interval=None,
                 searchable=False,
                 exportable=False,
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
            show_header (bool, optional): Whether to show the title / header of the card.
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
                             show_header=show_header,
                             header_icon=header_icon,
                             header_css_class=header_css_class,
                             ajax_reload=ajax_reload,
                             reload_interval=reload_interval,
                             searchable=searchable,
                             exportable=exportable,
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


    def add_panel_layout(self, card_name='panel_layout', layout_id=None,
                         direction=PanelSplit.HORIZONTAL,
                         resizable=True, full_height=True, min_height='400px',
                         css_class='', css_style='', persist=True):
        """
        Creates a CSS Grid-based panel layout with resizable and collapsible regions.

        Returns a PanelLayout object. Define the structure using its root split,
        then add cards to regions. Call layout.render() to get the card for use
        in add_card_group().

        Example:
            layout = self.add_panel_layout()
            root = layout.root

            sidebar = root.add_region('sidebar', size='250px', collapsible=True)
            right = root.add_split(direction='vertical')
            header = right.add_region('header', size='auto')
            main = right.add_region('main', size='1fr')

            sidebar.add_card(nav_card)
            main.add_card(content_card)

            self.add_card_group(layout.render(), div_css_class='col-12')

        Args:
            card_name (str, optional): Card name for the wrapper card. Defaults to 'panel_layout'.
            layout_id (str, optional): HTML id for the layout container.
            direction (str, optional): Root split direction - 'horizontal' or 'vertical'.
            resizable (bool, optional): Whether panels can be resized by dragging. Defaults to True.
            full_height (bool, optional): Whether to fill viewport height. Defaults to True.
            min_height (str, optional): CSS min-height when full_height is True. Defaults to '400px'.
            css_class (str, optional): Additional CSS classes for the layout container.
            css_style (str, optional): Additional inline styles for the layout container.

        Returns:
            PanelLayout: The layout object to configure and render.
        """
        layout = PanelLayout(
            view=self,
            card_name=card_name,
            layout_id=layout_id,
            direction=direction,
            resizable=resizable,
            full_height=full_height,
            min_height=min_height,
            css_class=css_class,
            css_style=css_style,
            persist=persist,
        )
        return layout

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

    def add_message_card(self, card_name=None, title=None, message='', **kwargs):
        """
        Adds a message / warning card
        """
        card = self.add_card(
            card_name=card_name,
            group_type=CARD_TYPE_CARD_MESSAGE,
            title=title,
            extra_card_context={'message': message},
            **kwargs
        )
        return card

    def add_linked_datatables_card(self, card_name=None, title='Linked Datatables', datatables=None, **kwargs):
        """
        Adds a card containing multiple datatables displayed side by side.

        Clicking a row in one datatable filters the next datatable in the chain.
        Each datatable config is a dict with:
            - id (str): Unique table identifier, used as the table_id and to find setup_table_<id> methods.
            - model (Model): The Django model for this datatable.
            - title (str, optional): Display title above this datatable.
            - linked_field (str, optional): The model field to filter on when a row is selected in the previous table.
            - css_class (str, optional): Extra CSS class for the datatable's column div.

        Example:
            self.add_linked_datatables_card(
                card_name='drilldown',
                title='Company Drilldown',
                datatables=[
                    {'id': 'categories', 'model': CompanyCategory, 'title': 'Categories'},
                    {'id': 'companies', 'model': Company, 'title': 'Companies',
                     'linked_field': 'company_category_id'},
                    {'id': 'people', 'model': Person, 'title': 'People',
                     'linked_field': 'company_id'},
                ]
            )
        """
        if datatables is None:
            datatables = []
        return self.add_card(
            card_name=card_name,
            title=title,
            group_type=CARD_TYPE_LINKED_DATATABLES,
            datatables=datatables,
            **kwargs
        )

    def add_accordion_card(self, card_name=None, title=None, panels=None, multi_open=False,
                           full_height=False, min_height='300px', **kwargs):
        """
        Adds an accordion card containing multiple collapsible panels.

        Each panel can contain any type of card content. Panels can optionally
        load their content via AJAX when first expanded.

        Args:
            card_name (str, optional): Unique card identifier.
            title (str, optional): Card header title. If None, no card header is shown.
            panels (list): List of panel config dicts, each with:
                - card (CardBase): A card instance to render as the panel body.
                - title (str): Panel header text.
                - id (str, optional): Unique panel identifier.
                - expanded (bool, optional): Whether panel starts expanded. First panel defaults to True.
                - icon (str, optional): Font Awesome icon class for the panel header.
                - header_css_class (str, optional): Extra CSS class for the panel header.
                - ajax_load (bool, optional): If True, panel content loads via AJAX on first expand.
            multi_open (bool): If True, multiple panels can be open at once. Default False.
            full_height (bool): If True, accordion fills remaining viewport height. Default False.
            min_height (str): Minimum height CSS value when full_height is True. Default '300px'.

        Example:
            detail_card = self.add_card(title='Details')
            detail_card.add_rows('name', 'email')

            table_card = self.add_card(
                card_name='items_table',
                group_type=CARD_TYPE_DATATABLE,
                datatable_model=Item
            )

            self.add_accordion_card(
                card_name='my_accordion',
                title='Info',
                panels=[
                    {'title': 'Details', 'card': detail_card, 'icon': 'fas fa-info-circle'},
                    {'title': 'Items', 'card': table_card, 'expanded': False},
                    {'title': 'Lazy Panel', 'ajax_load': True, 'expanded': False},
                ]
            )
        """
        if panels is None:
            panels = []
        return self.add_card(
            card_name=card_name,
            title=title,
            group_type=CARD_TYPE_ACCORDION,
            panels=panels,
            multi_open=multi_open,
            full_height=full_height,
            min_height=min_height,
            show_header=title is not None,
            **kwargs
        )

    def add_iframe_card(self, card_name=None, title=None, iframe_url='', iframe_srcdoc='',
                        iframe_height='400px', iframe_sandbox='allow-scripts allow-same-origin',
                        **kwargs):
        """
        Adds an iframe card that embeds external content or inline HTML in a sandboxed iframe.

        Use `iframe_url` to load a URL, or `iframe_srcdoc` to provide inline HTML content
        (e.g. a Three.js scene, a chart, or any self-contained HTML page).

        Args:
            card_name (str, optional): Unique card identifier.
            title (str, optional): Card header title. If None, no header is shown.
            iframe_url (str, optional): URL to load in the iframe.
            iframe_srcdoc (str, optional): Inline HTML content for the iframe.
            iframe_height (str, optional): CSS height of the iframe. Defaults to '400px'.
                Use '100%' when inside a panel layout region for full-height.
            iframe_sandbox (str, optional): Sandbox attribute value. Defaults to
                'allow-scripts allow-same-origin'.
            **kwargs: Additional keyword arguments passed to `add_card`.

        Returns:
            object: The card object.

        Example:
            # Load an external URL
            self.add_iframe_card(
                card_name='docs',
                title='Documentation',
                iframe_url='https://docs.djangoproject.com/',
            )

            # Inline HTML (e.g. Three.js, D3, etc.)
            self.add_iframe_card(
                card_name='scene',
                title='3D Viewer',
                iframe_srcdoc='<html><body><h1>Hello</h1></body></html>',
                iframe_height='500px',
            )
        """
        return self.add_card(
            card_name=card_name,
            title=title,
            group_type=CARD_TYPE_IFRAME,
            iframe_url=iframe_url,
            iframe_srcdoc=iframe_srcdoc,
            iframe_height=iframe_height,
            iframe_sandbox=iframe_sandbox,
            show_header=title is not None,
            **kwargs,
        )

    def add_treegrid_card(self, card_name=None, title=None, treegrid_data_url='',
                          treegrid_columns=None, treegrid_read_only=True,
                          treegrid_height='600px', treegrid_indentation=20,
                          treegrid_icon_map=None, treegrid_show_filter=True,
                          treegrid_expand_all=False, treegrid_show_column_filters=False,
                          treegrid_toolbar=None, treegrid_header_rows=None,
                          treegrid_node_column=0, treegrid_save_mode='auto',
                          treegrid_data_mode='ajax', treegrid_static_data=None,
                          treegrid_checkbox=False, treegrid_checkbox_column=0,
                          treegrid_context_menu=None, treegrid_resizable=False,
                          **kwargs):
        """
        Adds a treegrid card using Fancytree for hierarchical data display.

        The treegrid renders a tree table with lazy-loaded children, optional inline
        editing, filtering, and expand/collapse controls.

        Args:
            card_name (str, optional): Unique card identifier.
            title (str, optional): Card header title.
            treegrid_data_url (str): URL that returns JSON tree data. Must support
                a `parent` query parameter for lazy loading child nodes.
            treegrid_columns (list): Column definitions. Each is a dict with:
                - 'title' (str): Column header text.
                - 'field' (str): Data field name (from node.data).
                - 'width' (str, optional): CSS width.
                - 'editable' (bool, optional): Whether this column is editable.
            treegrid_read_only (bool): If True, disables inline editing. Defaults to True.
            treegrid_height (str): CSS max-height for the scrollable area. Defaults to '600px'.
            treegrid_indentation (int): Pixels of indentation per tree level. Defaults to 20.
            treegrid_icon_map (dict, optional): Maps node data 'type' values to FontAwesome
                classes, e.g. {'company': 'fas fa-building', 'person': 'fas fa-user'}.
            treegrid_show_filter (bool): If True, shows the search/filter toolbar. Defaults to True.
            treegrid_expand_all (bool): If True, expands all nodes on initial load. Defaults to False.
            treegrid_show_column_filters (bool): If True, shows a per-column filter row below headers.
            treegrid_toolbar (list, optional): Custom toolbar buttons. Each is a dict with:
                - 'label' (str): Button text.
                - 'icon' (str, optional): FontAwesome class (e.g. 'fas fa-plus').
                - 'name' (str): Identifier posted back as button_{card_name}_{name}.
            **kwargs: Additional keyword arguments passed to `add_card`.

        Returns:
            object: The card object.

        Example:
            self.add_treegrid_card(
                card_name='org_tree',
                title='Organisation',
                treegrid_data_url=reverse('org_tree_data'),
                treegrid_columns=[
                    {'title': 'Name', 'field': 'title', 'width': '40%'},
                    {'title': 'Role', 'field': 'role', 'width': '30%', 'editable': True},
                    {'title': 'Email', 'field': 'email', 'width': '30%'},
                ],
                treegrid_read_only=False,
                treegrid_icon_map={
                    'department': 'fas fa-building',
                    'person': 'fas fa-user',
                },
            )
        """
        if treegrid_columns is None:
            treegrid_columns = []
        if treegrid_icon_map is None:
            treegrid_icon_map = {}
        return self.add_card(
            card_name=card_name,
            title=title,
            group_type=CARD_TYPE_TREEGRID,
            treegrid_data_url=treegrid_data_url,
            treegrid_columns=treegrid_columns,
            treegrid_read_only=treegrid_read_only,
            treegrid_height=treegrid_height,
            treegrid_indentation=treegrid_indentation,
            treegrid_icon_map=treegrid_icon_map,
            treegrid_show_filter=treegrid_show_filter,
            treegrid_expand_all=treegrid_expand_all,
            treegrid_show_column_filters=treegrid_show_column_filters,
            treegrid_toolbar=treegrid_toolbar or [],
            treegrid_header_rows=treegrid_header_rows or [],
            treegrid_node_column=treegrid_node_column,
            treegrid_save_mode=treegrid_save_mode,
            treegrid_data_mode=self._resolve_treegrid_data_mode(
                treegrid_data_mode, treegrid_data_url, treegrid_static_data),
            treegrid_static_data=treegrid_static_data or [],
            treegrid_checkbox=treegrid_checkbox,
            treegrid_checkbox_column=treegrid_checkbox_column,
            treegrid_context_menu=treegrid_context_menu or [],
            treegrid_context_menu_html=self._build_context_menu_html(
                treegrid_context_menu, card_name),
            treegrid_resizable=treegrid_resizable,
            show_header=title is not None,
            **kwargs,
        )

    def _build_context_menu_html(self, menu_items, card_name):
        """Build context menu HTML from MenuItem/DividerItem objects.

        Dicts are skipped (handled by JS). MenuItems are rendered into
        a dropdown-menu div that the JS positions on right-click.
        """
        if not menu_items:
            return ''
        from django_menus.menu import HtmlMenu, BaseMenuItem
        # Filter to MenuItem/DividerItem objects only
        menu_objs = [i for i in menu_items if isinstance(i, BaseMenuItem)]
        if not menu_objs:
            return ''
        menu = HtmlMenu(request=self.request, template='dropdown',
                        menu_id=f'{card_name}_context_menu', no_hover=True)
        menu.add_items(*menu_objs)
        return menu.render()

    @staticmethod
    def _resolve_treegrid_data_mode(explicit_mode, data_url, static_data):
        """Infer data mode: url if a URL is given, static if data is given, else ajax."""
        if explicit_mode != 'ajax':
            return explicit_mode  # User explicitly chose
        if data_url:
            return 'url'
        if static_data:
            return 'static'
        return 'ajax'

    def treegrid_update_cell(self, card_name, key, field, value):
        """Add a command to update a single cell value in the treegrid.

        Example::

            self.treegrid_update_cell('my_tree', 'company_1', 'name', 'New Name')
            return self.command_response()
        """
        self.add_command('treegrid_update_cell', card=card_name, key=key, field=field, value=value)

    def treegrid_style_cell(self, card_name, key, field, bg=None, color=None,
                            css_class=None, remove_class=None):
        """Add a command to style a specific cell in the treegrid.

        Example::

            self.treegrid_style_cell('my_tree', 'company_1', 'status',
                                     bg='#d4edda', color='#155724')
            return self.command_response()
        """
        cmd = {'card': card_name, 'key': key, 'field': field}
        if bg:
            cmd['bg'] = bg
        if color:
            cmd['color'] = color
        if css_class:
            cmd['css_class'] = css_class
        if remove_class:
            cmd['remove_class'] = remove_class
        self.add_command('treegrid_style_cell', **cmd)

    def treegrid_style_row(self, card_name, key, bg=None, color=None,
                           css_class=None, remove_class=None):
        """Add a command to style an entire row in the treegrid.

        Example::

            self.treegrid_style_row('my_tree', 'company_1', bg='#fff3cd')
            return self.command_response()
        """
        cmd = {'card': card_name, 'key': key}
        if bg:
            cmd['bg'] = bg
        if color:
            cmd['color'] = color
        if css_class:
            cmd['css_class'] = css_class
        if remove_class:
            cmd['remove_class'] = remove_class
        self.add_command('treegrid_style_row', **cmd)

    def treegrid_reload_response(self, card_name, **kwargs):
        """Return a command response that reloads the specified treegrid.

        Can be combined with other commands, e.g.::

            from ajax_helpers.utils import toast_commands
            self.add_command(toast_commands(header='Saved', text='Done'))
            return self.treegrid_reload_response('my_tree')
        """
        self.add_command('reload_treegrid', card=card_name)
        return self.command_response(**kwargs) if kwargs else self.command_response()

    def treegrid_add_node(self, card_name, parent_key, node_data, mode='child'):
        """Add a command to insert a node into the treegrid.

        Args:
            card_name: The treegrid card name.
            parent_key: Key of the target node. None to add to root.
            node_data: Dict with node properties (title, key, folder, data, etc.)
            mode: 'child' (add as child), 'before', or 'after' the target node.
        """
        self.add_command('treegrid_add_node', card=card_name,
                         parent_key=parent_key, node_data=node_data, mode=mode)

    def treegrid_remove_node(self, card_name, key):
        """Add a command to remove a node from the treegrid."""
        self.add_command('treegrid_remove_node', card=card_name, key=key)

    def treegrid_move_node(self, card_name, key, target_key, mode='child'):
        """Add a command to move a node within the treegrid.

        Args:
            mode: 'child' (move into target), 'before', or 'after' the target.
        """
        self.add_command('treegrid_move_node', card=card_name,
                         key=key, target_key=target_key, mode=mode)

    def add_link_gallery_card(self, links, card_name=None, title='Links', show_image_names=False, **kwargs):
        """
        Adds a links gallery card with visual tiles for different link types.

        Each link dict should have:
          - 'url' (str): The link URL.
          - 'name' (str, optional): Display name for the link.
          - 'type' (str): One of 'image', 'data_sheet', 'product_page', 'other'.

        Images are shown as thumbnails with lightbox. Data sheets open in a new tab.
        Product pages and other links open in a new browser tab.

        Args:
            links (list[dict]): List of link dicts.
            card_name (str, optional): Unique card identifier.
            title (str, optional): Card header title. Defaults to 'Links'.
            show_image_names (bool, optional): Whether to show names below image thumbnails. Defaults to False.
            **kwargs: Additional keyword arguments passed to `add_card`.

        Returns:
            object: The card object, or None if links is empty.
        """
        if not links:
            # language=HTML
            html = '<div style="padding: 20px;"><p class="text-center">No links</p></div>'
            return self.add_card(
                card_name=card_name,
                title=title,
                group_type=CARD_TYPE_HTML,
                html=html,
                **kwargs,
            )
        # Assign image_index for lightbox navigation (only counting image-type links)
        image_idx = 0
        for link in links:
            if link.get('type') == 'image':
                link['image_index'] = image_idx
                image_idx += 1
        return self.add_card(
            card_name=card_name,
            title=title,
            template_name='image_gallery',
            extra_card_context={'links': links, 'show_image_names': show_image_names},
            **kwargs,
        )

    def add_image_gallery_card(self, images, card_name=None, title='Images', **kwargs):
        """
        Adds an image gallery card with thumbnail grid and lightbox modal.

        This is a convenience wrapper around ``add_link_gallery_card()`` for image-only galleries.

        Args:
            images (list[dict]): List of dicts with 'url' and optional 'name' keys.
            card_name (str, optional): Unique card identifier.
            title (str, optional): Card header title. Defaults to 'Images'.
            **kwargs: Additional keyword arguments passed to `add_card`.

        Returns:
            object: The card object, or None if images is empty.
        """
        if not images:
            # language=HTML
            html = '<div style="padding: 20px;"><p class="text-center">No images</p></div>'
            return self.add_card(
                card_name=card_name,
                title=title,
                group_type=CARD_TYPE_HTML,
                html=html,
                **kwargs,
            )
        return self.add_card(
            card_name=card_name,
            title=title,
            template_name='image_gallery',
            extra_card_context={'images': images},
            **kwargs,
        )

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

    def reload_card(self, card_code):
        """Add a command to tell the client to reload a specific card via AJAX.

        Usage from any button handler:
            def button_save(self, **kwargs):
                # ... save logic ...
                self.reload_card('my_card')
                return self.command_response('null')
        """
        self.add_command('reload_card', card=card_code)

    def button_reload_card(self, **kwargs):
        card_code = kwargs.get('card')
        if not hasattr(self, 'object') and hasattr(self, 'get_object'):
            self.object = self.get_object()
        self.cards = {}
        self.card_groups = {}
        self.tables = {}
        self.setup_datatable_cards()
        self.setup_cards()
        card = self.cards.get(card_code)
        if card is not None:
            return self.command_response('html', selector=f'#{card.code}_ajax', html=card._render_template())
        return self.command_response('null')

    def button_accordion_load(self, **kwargs):
        """AJAX handler to load an accordion panel's content on first expand."""
        accordion_code = kwargs.get('accordion')
        panel_id = kwargs.get('panel_id')
        if not hasattr(self, 'object') and hasattr(self, 'get_object'):
            self.object = self.get_object()
        self.cards = {}
        self.card_groups = {}
        self.tables = {}
        self.setup_datatable_cards()
        self.setup_cards()
        accordion = self.cards.get(accordion_code)
        if accordion is not None:
            for panel in accordion.extra_card_info.get('initialized_panels', []):
                if panel['id'] == panel_id and panel.get('card'):
                    html = panel['card'].render()
                    return self.command_response('html', selector=f'#{panel_id}_content', html=html)
        return self.command_response('null')
