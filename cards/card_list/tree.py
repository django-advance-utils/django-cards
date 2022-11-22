import json

from ajax_helpers.mixins import AjaxHelpers
from django_menus.menu import MenuMixin

from cards.base import CARD_TYPE_HTML
from cards.card_list.base import CardListBaseMixin
from cards.standard import CardMixin


class CardTreeMixin(CardListBaseMixin):

    show_details_for_parents = False

    def get_default_selected_id(self):
        return ''

    def add_tree_card(self):
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
        self.add_tree_card()
        self.add_card('details_card',
                      group_type=CARD_TYPE_HTML,
                      template_name='blank')

        self.add_card_group('tree_card', div_css_class=self.list_class)
        self.add_card_group('details_card', div_css_class=self.details_class)

    def get_tree_data(self, selected_id):
        return []


class CardTree(AjaxHelpers, MenuMixin, CardMixin, CardTreeMixin):
    pass
