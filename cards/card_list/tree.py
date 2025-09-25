import json

from ajax_helpers.mixins import AjaxHelpers
from django_menus.menu import MenuMixin

from cards.base import CARD_TYPE_HTML
from cards.card_list.base import CardListBaseMixin
from cards.standard import CardMixin


class CardTreeMixin(CardListBaseMixin):
    """
    Mixin for displaying a tree-style card layout with selectable nodes and optional detail view.

    Provides a reusable structure for rendering hierarchical data in a card interface using a tree component.
    Typically used in views that require a tree navigation sidebar and a corresponding details panel.

    Attributes:
        show_details_for_parents (bool): If True, allows parent nodes to show detail views.
    """

    show_details_for_parents = False

    def get_default_selected_id(self):
        """
        Returns the default selected ID used when no selection is present in the URL slug.

        Returns:
           str: The default selected node ID. Defaults to empty string.
        """
        return ''

    def add_tree_card(self):
        """
        Adds a tree navigation card to the card layout.

        The tree is populated using data from `get_tree_data()` and marks the appropriate node as selected
        based on the current slug or default ID. Also expands parent nodes as needed.
        """
        list_menu = self.get_list_menu()

        selected_id = self.slug.get('pk')

        if not selected_id or selected_id == '-':
            selected_id = self.get_default_selected_id()

        tree_data = self.get_tree_data(selected_id=selected_id)

        for row in tree_data:
            if row['id'] == selected_id:
                if 'state' in row:
                    row['state']['selected'] = True
                else:
                    row['state'] = {'selected': True}
                    self.open_parent(tree_data=tree_data, parent_id=row['parent'])
                    break

        context = {'list_title': self.list_title,
                   'data': json.dumps(tree_data),
                   'selected_id': selected_id,
                   'details_button_action_name': 'details_html',
                   'show_details_for_parents': self.show_details_for_parents}

        self.add_card('tree_card',
                      title=self.list_title,
                      menu=list_menu,
                      group_type=CARD_TYPE_HTML,
                      template_name='tree_selection',
                      extra_card_context=context)

    def open_parent(self, tree_data, parent_id):
        """
        Recursively opens parent nodes to ensure visibility of the selected child node.

        Args:
            tree_data (list): The full tree data structure.
            parent_id (str): The parent node ID to expand.
        """
        if parent_id == '#':
            return
        for row in tree_data:
            if row['id'] == parent_id:
                if 'state' in row:
                    row['state']['opened'] = True
                else:
                    row['state'] = {'opened': True}
                    self.open_parent(tree_data=tree_data, parent_id=row['parent'])
                    break

    def setup_cards(self):
        """
        Defines and groups cards for the tree and detail view.

        This method is automatically called during context setup, and
        it adds both the tree navigation card and the blank detail card.
        """
        self.add_tree_card()
        self.add_card('details_card',
                      group_type=CARD_TYPE_HTML,
                      template_name='blank')

        self.add_card_group('tree_card', div_css_class=self.list_class)
        self.add_card_group('details_card', div_css_class=self.details_class)

    def get_tree_data(self, selected_id):
        """
        Returns the tree structure to be rendered in the tree card.

        This method should be overridden in a subclass to return actual tree data.

        Args:
            selected_id (str): The currently selected node ID.

        Returns:
            list: A list of dictionaries representing tree nodes.
        """
        return []


class CardTree(AjaxHelpers, MenuMixin, CardMixin, CardTreeMixin):
    """
    Composite view mixin class for rendering hierarchical (tree-based) data with detail cards.

    This class combines:
        - `AjaxHelpers`: Enables AJAX button handling and dynamic updates.
        - `MenuMixin`: Adds view/card menu support.
        - `CardMixin`: Core functionality for managing and rendering cards.
        - `CardTreeMixin`: Adds a tree navigation panel with expandable/collapsible nodes and detail view integration.

    Designed for views where the user selects from a tree structure (e.g., categories or nested objects),
    and a detail card is shown alongside the tree.

    Example usage:
        class MyTreeView(CardTree):
            list_title = "Departments"
            def get_tree_data(self, selected_id):
                ...

    """
    pass
