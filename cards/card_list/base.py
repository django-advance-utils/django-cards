from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django_datatables.reorder_datatable import reorder

from cards.base import CARD_TYPE_STANDARD, CardBase, CARD_TYPE_HTML


class CardListBaseMixin:
    """
    Base mixin to support rendering of detail cards and card groups within a list-detail view layout.

    This mixin provides common methods and hooks for:
    - Slug processing and permission gating via `dispatch`
    - Detail card creation and rendering
    - Optional HTML group card rendering
    - Hook points for customizing menu, title, footer, and other card attributes

    Attributes:
        list_class (str): CSS class for the left-hand list column layout.
        details_class (str): CSS class for the right-hand details column layout.
        model (Model): Django model used to fetch detail objects.
        datatable_model (Model): Optional model used in datatable-based cards.
        list_title (str): Default title for list view cards.
        menu_display (str): Used for display hints on how to show menu (unused by default).
        card_cls (class): The class used to instantiate new card objects.
    """
    list_class = 'col-sm-5 col-md-4 col-lg-3 float-left'
    details_class = 'col-sm-7 col-md-8 col-lg-9 float-left'

    model = None
    datatable_model = None
    order_field = 'order'
    list_title = ''
    menu_display = ''
    card_cls = CardBase

    def __init__(self):
        super().__init__()
        self.slug = {}
        self.cards = {}

    def dispatch(self, request, *args, **kwargs):
        self.split_slug(kwargs)
        if self.process_slug_kwargs():
            # noinspection PyUnresolvedReferences
            return super().dispatch(request, *args, **self.kwargs)
        else:
            raise Exception('User does not have permission')

    def get_card_template(self):
        """
        Returns a custom template name for the detail card, if needed.

        Override this method to specify a different template for rendering the detail card.
        If None is returned, the card will fall back to its default template.

        Returns:
            str or None: Template path or None to use default.
        """
        return None

    def get_card_footer(self, details_object):
        """
        Returns footer content for the detail card.

        Override this to append a custom footer string to the rendered card, such as
        disclaimers, summaries, or action links.

        Args:
           details_object (object): The object being displayed in the card.

        Returns:
           str: Footer HTML/text content. Defaults to empty string.
        """
        return ''

    def get_show_created_modified_dates(self, details_object):
        """
        Determines whether to show created/modified timestamps on the detail card.

        Override this method to toggle visibility of audit fields depending on the object
        or view context.

        Args:
            details_object (object): The object being displayed.

        Returns:
            bool: True to show created/modified dates, False to hide them. Defaults to True.
        """
        return True

    def get_extra_card_kwargs(self, details_object):
        """
        Hook for injecting additional keyword arguments into the detail card constructor.

        Override this method in your subclass to pass custom options or flags into the card,
        based on the current `details_object`.

        Args:
            details_object (object): The object to be displayed in the detail card.

        Returns:
            dict: A dictionary of extra keyword arguments for `add_detail_card()`.
        """
        return {}

    def button_details_html(self, extra_card_context=None, **kwargs):
        """
        Triggered when a list item is clicked; renders the details card for the selected entry.

        This method is typically bound to the list card and responds via Ajax when a user clicks on a row.
        It retrieves the corresponding object using `entry_id`, and either:
         - Calls `setup_details_cards(details_object=...)` if defined, or
         - Uses `add_main_card()` to create a default detail card.

        The resulting cards are rendered and returned as an HTML update for the `#details_card` container.

        Args:
            extra_card_context (dict, optional): Extra context passed into the detail card(s).
            **kwargs: Expected to contain 'entry_id' (the PK of the clicked list item).

        Returns:
            JsonResponse: A command response replacing the `#details_card` element's content.
        """
        details_object = self.get_details_object(pk=kwargs['entry_id'])

        if hasattr(self, 'setup_details_cards'):
            self.setup_details_cards(details_object=details_object)
        else:
            self.add_main_card(details_object=details_object, extra_card_context=extra_card_context)

        data = self._render_cards()
        return self.command_response('html', selector='#details_card', html=data)

    # noinspection PyMethodMayBeStatic
    def process_slug_kwargs(self):
        """
        Hook for validating or modifying slug-derived kwargs before dispatch.

        Override this method to implement permission checks or slug-based filtering.
        If it returns False, dispatch will be blocked with an exception.

        Returns:
           bool: True if the view should continue processing, False to deny access.
        """
        return True

    def split_slug(self, kwargs):
        """
        Internal: Parses and splits the 'slug' from view kwargs into the `self.slug` dictionary.

        Handles both single-key slugs (e.g., `'123'`) and compound slugs with key-value pairs
        (e.g., `'type-user-id-42'` becomes `{'type': 'user', 'id': '42'}`).

        Also sets `self.kwargs['pk']` if 'pk' is found in the slug, to maintain compatibility
        with Django's detail views.

        Args:
            kwargs (dict): The keyword arguments passed to the view (typically from URL routing).
        """
        if 'slug' in kwargs:
            if not hasattr(self, 'slug'):
                self.slug = {}
            if kwargs['slug'] == '-':
                self.slug['pk'] = '-'
            else:
                s = kwargs['slug'].split('-')
                if len(s) == 1:
                    self.slug['pk'] = s[0]
                else:
                    self.slug.update({s[k]: s[k+1] for k in range(0, int(len(s)-1), 2)})
                if 'pk' in self.slug:
                    self.kwargs['pk'] = self.slug['pk']

    def add_main_card(self, details_object, extra_card_context=None, code='main'):
        """
        Creates and registers the main detail card for the selected object.

        This method configures and instantiates the primary card associated with a selected list
        or tree entry. It gathers common settings such as title, menu, footer, and template by
        calling overridable hooks like `get_details_title()` and `get_card_template()`.

        The resulting card is typically used in the right-hand details panel of a list-detail or tree-detail layout.

        Args:
            details_object (object): The object to render inside the detail card.
            extra_card_context (dict, optional): Additional context variables for the card template. Defaults to empty dict.
            code (str, optional): The key to register the card under (default is `'main'` for standard layouts).

        Returns:
            CardBase: The created and registered card instance.
        """
        if extra_card_context is None:
            extra_card_context = {}
        menu = self.get_details_menu(details_object=details_object)
        title = self.get_details_title(details_object=details_object)
        group_type = self.get_group_type(details_object=details_object)
        footer = self.get_card_footer(details_object=details_object)
        show_created_modified_dates = self.get_show_created_modified_dates(details_object=details_object)
        extra_card_kwargs = self.get_extra_card_kwargs(details_object=details_object)
        template_name = self.get_card_template()
        card = self.add_detail_card(title=title,
                                    code=code,
                                    details_object=details_object,
                                    menu=menu,
                                    show_created_modified_dates=show_created_modified_dates,
                                    group_type=group_type,
                                    footer=footer,
                                    datatable_model=self.datatable_model,
                                    extra_card_context=extra_card_context,
                                    template_name=template_name,
                                    **extra_card_kwargs)
        return card

    def add_detail_card(self, code=None, details_object=None, title=None, menu=None, tab_menu=None, template_name=None,
                        group_type=CARD_TYPE_STANDARD, show_created_modified_dates=False,
                        footer=None, extra_card_context=None, call_details_data=True, **extra_card_kwargs):
        """
        Creates and registers a new detail card for displaying object-specific information.

        This is a flexible, lower-level method used to instantiate a card (typically of `CardBase` type or a subclass)
        with custom configuration. Cards created here are registered in `self.cards` under the provided `code`.

        Args:
            code (str, optional): Unique identifier for the card (used as a key in `self.cards`).
            details_object (object, optional): The object containing data to display on the card.
            title (str, optional): The card’s display title.
            menu (list, optional): A list of menu actions for the card.
            tab_menu (list, optional): A list of tabbed actions or views for the card.
            template_name (str, optional): The template to use when rendering the card.
            group_type (str, optional): Layout type for the card (e.g., standard, HTML). Defaults to `CARD_TYPE_STANDARD`.
            show_created_modified_dates (bool, optional): If True, includes created/modified dates. Defaults to False.
            footer (str, optional): Footer content for the card.
            extra_card_context (dict, optional): Additional context data for the card’s template.
            call_details_data (bool, optional): Whether to call the card’s `get_details_data()` method. Defaults to True.
            **extra_card_kwargs: Additional keyword arguments passed to the card constructor.

        Returns:
            CardBase: The created card instance.
        """
        card = self.card_cls(request=self.request,
                             view=self,
                             code=code,
                             title=title,
                             menu=menu,
                             tab_menu=tab_menu,
                             show_created_modified_dates=show_created_modified_dates,
                             footer=footer,
                             group_type=group_type,
                             details_object=details_object,
                             extra_card_context=extra_card_context,
                             template_name=template_name,
                             call_details_data=call_details_data,
                             **extra_card_kwargs)

        self.cards[code] = card
        return card

    def add_html_group(self, context_template_name, context, **kwargs):
        """
        Renders a template to HTML and wraps it in a card of type `CARD_TYPE_HTML`.

        This is useful for injecting arbitrary HTML content into a detail card area
        without needing a full object context.

        Args:
           context_template_name (str): The name of the template to render.
           context (dict): The context data for rendering the template.
           **kwargs: Additional keyword arguments passed to `add_detail_card()`.

        Returns:
           CardBase: The created HTML card.
        """
        html = render_to_string(context_template_name, context)
        card = self.add_detail_card(group_type=CARD_TYPE_HTML,
                                    html=html,
                                    **kwargs)
        return card

    def _render_cards(self):
        """
        Renders all registered cards using their `render()` method.

        This method is used internally when a new card layout needs to be sent
        back to the client after an action (e.g., selecting an item from a list).

        Returns:
            str: Combined rendered HTML for all cards in `self.cards`.
        """
        data = ""
        for card_key, card in self.cards.items():
            data += card.render()
        return data

    def get_details_data(self, card, details_object):
        """
        Hook for populating extra data into a detail card.

        Intended to be overridden in subclasses. The default implementation does nothing.

        Args:
            card (CardBase): The card being populated.
            details_object (object): The object the card is representing.
        """

    def get_details_object(self, pk):
        """
        Retrieves the details object for the given primary key.

        By default, this uses Django’s `get_object_or_404()` with `self.model`.
        If `self.model` is None, the PK itself is returned (useful for testing or loose contexts).

        Args:
            pk (int or str): The primary key to fetch.

        Returns:
            object: The retrieved object or raw PK.
        """
        if self.model is None:
            return pk
        return get_object_or_404(self.model, pk=pk)

    def get_details_menu(self, details_object):
        """
        Returns the menu actions for the detail card of the given object.

        Can be overridden to supply custom menu items based on the object.

        Args:
           details_object (object): The object being shown in the detail card.

        Returns:
           list: A list of menu items (dictionaries or other supported format).
        """
        return []

    def get_details_title(self, details_object):
        """
        Returns the title text to display on the detail card.

        Can be overridden to derive a dynamic title from the object.

        Args:
            details_object (object): The object shown in the card.

        Returns:
            str: The card title. Defaults to "Details".
        """
        return 'Details'

    def get_group_type(self, details_object):
        """
        Returns the group type for the detail card, used to determine its layout.

        Can be overridden for custom logic (e.g., based on object type or status).

        Args:
            details_object (object): The object shown in the card.

        Returns:
            str: A group type constant such as `CARD_TYPE_STANDARD`.
        """
        return CARD_TYPE_STANDARD

    def get_list_menu(self):
        """
        Returns a list of menu items to be displayed on the list card (left panel).

        This is typically used to provide context actions related to the list itself,
        such as "Add New", "Filter", or "Export".

        Override this method to return a list of dictionaries, where each dictionary
        represents a menu item with keys like:
           - 'label': The display text (e.g., "Add New")
           - 'icon': Optional icon class (e.g., "fa fa-plus")
           - 'action': The JS function or URL to trigger
           - 'confirm': Optional confirmation prompt
           - 'permission': Optional permission check

        Returns:
           list: A list of menu item dictionaries. Defaults to an empty list.
        """
        return []

    def button_save_list_order(self, **kwargs):
        reorder(model=self.model, order_field=self.order_field, sort_data=kwargs['sort'])
        return self.command_response('null')