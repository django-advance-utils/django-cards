from ajax_helpers.mixins import AjaxHelpers
from django.utils.safestring import mark_safe
from django_menus.menu import MenuMixin

from cards.base import CARD_TYPE_HTML
from cards.card_list.base import CardListBaseMixin
from cards.standard import CardMixin


class CardListMixin(CardListBaseMixin):
    """
    Mixin for displaying a list-detail layout using cards.

    Renders a left-hand list panel with selectable items and a right-hand detail card.
    Designed for use in Django views that follow a list-detail interaction model.

    Attributes:
        list_class (str): CSS class for styling the list column.
        details_class (str): CSS class for styling the details column.
        list_css_style (str): Inline CSS for the list column.
        details_css_style (str): Inline CSS for the details column.
        list_type (str or None): Describes the type of entries (used in empty message text).
        list_title (str): Title to display above the list.
        menu_display (str): Optional string controlling how the list menu is displayed.
        list_template_name (str): Template used for rendering the list card.
        model (Django Model): Model used to fetch list entries.
    """
    list_class = 'col-sm-5 col-md-4 col-lg-3 float-left'
    details_class = 'col-sm-7 col-md-8 col-lg-9 float-left'
    list_css_style = ''
    details_css_style = ''

    list_type = None
    list_title = ''
    menu_display = ''
    list_template_name = 'list_selection'

    model = None

    def setup_cards(self):
        """
        Sets up the list and detail cards, including layout configuration and default selection.
        """
        list_menu = self.get_list_menu()
        selected_id = self.get_selected_id()

        self.add_list_card(card_name='list_card',
                           list_entries=self.list_entries,
                           list_title=self.list_title,
                           selected_id=selected_id,
                           list_menu=list_menu,
                           list_template_name=self.list_template_name,
                           empty_list_message=self.empty_list_message())

        self.add_card('details_card',
                      group_type=CARD_TYPE_HTML,
                      template_name='blank',
                      html='')

        self.add_card_group('list_card', div_css_class=self.list_class, div_css=self.list_css_style)
        self.add_card_group('details_card', div_css_class=self.details_class, div_css=self.details_css_style)

    def get_selected_id(self):
        selected_id = self.slug.get('pk')
        self.display_list_entries()
        if (not selected_id or selected_id == '-') and self.list_entries:
            selected_id = self.get_default_selected_id()
        elif selected_id == '-':
            selected_id = ''

        if selected_id:
            selected_id = int(selected_id)
        return selected_id

    def get_default_selected_id(self):
        """
        Returns the default selected ID used when no selection is present in the URL slug.

        Returns:
           str: The default selected node ID. Defaults to empty string.
        """
        return self.list_entries[0]['pk']

    def empty_list_message(self):
        """
        Returns a user-friendly message for when the list has no entries.

        Returns:
            str: A message such as "No items setup yet!"
        """
        list_type = self.list_type if self.list_type is not None else self.list_title
        return f'No {list_type} setup yet!'

    def empty_details_message(self):
        """
        Returns a user-friendly message for when no details are available to show.

        Returns:
            str: A message such as "No items setup yet!"
        """
        list_type = self.list_type if self.list_type is not None else self.list_title
        return f'No {list_type} setup yet!'

    def get_empty_details_title(self):
        """
        Returns the title to use when displaying an empty detail view.

        Returns:
            str: The string "Details" by default.
        """
        return 'Details'

    def get_empty_details_menu(self):
        """
        Override this to return menu items when the details panel is empty.

        By default, this returns an empty list, meaning no menu actions will be
        shown when no detail item is selected. Override to provide context-specific
        actions in that case.

        Returns:
            list: A list of menu item dictionaries, or an empty list.
        """
        return []

    def button_empty_details_html(self, extra_card_context=None, **kwargs):
        """
        Renders a default message card for when no detail item is selected,
        and returns a command response to update the details card container.

        This is typically triggered when a list entry is not selected or is cleared,
        and is meant to inform the user that no item is being displayed.

        Args:
           extra_card_context (dict, optional): Additional context to pass into the card.
           **kwargs: Additional keyword arguments for extensibility.

        Returns:
           HttpResponse: A command response to replace the #details_card with rendered HTML.
        """
        card = self.add_card(title=self.get_empty_details_title(),
                             template_name='message',
                             menu=self.get_empty_details_menu(),
                             extra_card_context={'message': self.empty_details_message()})
        return self.command_response('html', selector='#details_card', html=card.render())

    def __init__(self):
        self.list_entries = []
        super().__init__()

    def add_list_entry(self, pk, name, colour=None, row_class=None):
        """
        Adds a single entry to the list card's entries collection.

        Args:
            pk (int or str): The primary key or unique ID for the entry.
            name (str): The display name of the entry. Will be marked safe for HTML.
            colour (str, optional): Optional badge or label colour to display alongside the entry.
            row_class (str, optional): Optional CSS class for styling the row.
        """
        self.list_entries.append({'pk': pk, 'name': mark_safe(name),
                                  'colour': colour, 'class': row_class if row_class else ''})

    def get_list_entry_name(self, entry_object):
        """
         Returns the display name for a given entry object.

         By default, attempts to access the 'name' attribute. Override or extend
         as needed for more complex representations.

         Args:
             entry_object (object): The model instance representing a list entry.

         Returns:
             str: The name to be displayed for the entry.
         """
        return getattr(entry_object, 'name', str(entry_object))

    def get_list_colour(self, entry_object):
        """
        Returns the colour associated with a list entry, if applicable.

        Can be overridden to assign contextual colours (e.g., based on status).

        Args:
           entry_object (object): The model instance representing a list entry.

        Returns:
           str or None: A colour name (e.g., 'green', 'red') or None for no colour.
        """
        return None

    def get_list_entries(self):
        """
        Retrieves the list of model instances to be used as entries in the list card.

        This method queries the model defined in `self.model`.

        Returns:
            QuerySet: The queryset of model instances.
        """
        return self.model.objects.all()

    def display_list_entries(self):
        """
        Fetches list entries and populates `self.list_entries` with formatted entries.

        Each entry is added using `add_list_entry()`. The formatting includes
        retrieving display name and optional colour per entry.
        """
        for entry_object in self.get_list_entries():
            name = self.get_list_entry_name(entry_object=entry_object)
            colour = self.get_list_colour(entry_object=entry_object)
            self.add_list_entry(pk=entry_object.pk,
                                name=name,
                                colour=colour)


class CardList(AjaxHelpers, MenuMixin, CardMixin, CardListMixin):
    """
    Composite view mixin class that provides full list-detail card rendering with AJAX support.

    This class combines the following functionality:
        - `AjaxHelpers`: Enables AJAX-based button and form handling.
        - `MenuMixin`: Adds support for view- or card-level menus.
        - `CardMixin`: Provides methods for creating and managing cards.
        - `CardListMixin`: Implements the list-detail layout with selectable list items and detail panel.

    Intended for use as a base class in views where a selectable list on the left displays
    detail information on the right via AJAX card rendering.

    Example usage:
        class MyView(CardList):
            model = MyModel
            list_title = "My Items"
            ...

    """
    pass
