from cards_examples.views.base import MainMenu
from django.views.generic import TemplateView
from django_menus.menu import MenuItem

from cards.base import CARD_TYPE_CARD_GROUP
from cards.standard import CardMixin


class ChildCardExampleIndex(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.setup_simple_example()
        self.setup_complex_example()
        self.add_card_group('simple', 'complex', div_css_class='col-12 float-left')

    def setup_simple_example(self):
        child_1_card = self.add_card(template_name='table_body')
        child_1_card.add_rows({'label': 'Label', 'value': 'Hello World'},
                              {'label': 'Description',
                               'value': 'This is a child card using template_name="table_body"'})

        child_2_card = self.add_card(template_name='table_body')
        child_2_card.add_rows({'label': 'Label', 'value': 'Hello World'},
                              {'label': 'Description', 'value': 'This is a another child card'})

        card = self.add_card('simple', title='Simple Example', group_type=CARD_TYPE_CARD_GROUP)
        card.add_child_card_group(child_1_card,
                                  div_css_class='col-6 float-left',
                                  div_inner_css='border-style: solid;border-color: red')
        card.add_child_card_group(child_2_card,
                                  div_css_class='col-6 float-left',
                                  div_inner_css='border-style: solid;background-color: #9a59b5;'
                                                'border-color: #9a59b5; color: white')

    def setup_complex_example(self):
        child_menu = [MenuItem('cards_examples:hello_modal', menu_display='Child Menu')]
        main_menu = [MenuItem('cards_examples:hello_modal', menu_display='Main Menu')]

        child_1_card = self.add_card(title='Card 1 Card', template_name='table', menu=child_menu)
        child_1_card.add_rows({'label': 'Label', 'value': 'Hello World'},
                              {'label': 'Description', 'value': 'This is a child card with a meny'})

        child_2_card = self.add_card(title='Card 2 Card', template_name='table')
        child_2_card.add_rows({'label': 'Label', 'value': 'Hello World'},
                              {'label': 'Description', 'value': 'This is a another child card'})

        card = self.add_card('complex', title='Complex Example', group_type=CARD_TYPE_CARD_GROUP,
                             menu=main_menu)
        card.add_child_card_group(child_1_card,
                                  div_css_class='col-6 float-left',
                                  div_inner_css='border-style: solid;border-color: red')
        card.add_child_card_group(child_2_card,
                                  div_css_class='col-6 float-left',
                                  div_inner_css='border-style: solid;border-color: #9a59b5')
