from ajax_helpers.mixins import AjaxHelpers
from django.views.generic import TemplateView
from django_menus.menu import MenuMixin, MenuItem

from cards.standard import CardMixin


class MainMenu(AjaxHelpers, MenuMixin):
    def setup_menu(self):
        # noinspection PyUnresolvedReferences
        self.add_menu('main_menu').add_items(
            ('cards_examples:index', 'Home'),
            ('cards_examples:groups', 'Groups'),
            MenuItem(url='admin:index',
                     menu_display='Admin',
                     visible=self.request.user.is_superuser),

        )


class ExampleIndex(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/index.html'

    def setup_cards(self):
        card = self.add_card('welcome', title='Welcome')
        card.add_entry(value='sample text', label='Sample')


class ExampleCardsIndex(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        card = self.add_card('welcome', title='Welcome')
        card.add_entry(value='sample text', label='Sample')

        card = self.add_card('extra', title='Extra')
        card.add_entry(value='sample text', label='Sample')

        card = self.add_card('right', title='Right')
        card.add_entry(value='sample text right', label='Sample')

        self.add_card_group('welcome', 'extra', div_css_class='col-6 float-left')
        self.add_card_group('right', div_css_class='col-6 float-right')
