from ajax_helpers.mixins import AjaxHelpers
from django.views.generic import TemplateView
from django_menus.menu import MenuMixin, MenuItem

from cards.standard import CardMixin
from cards_examples.models import Company


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

        company = Company.objects.first()
        if company is None:
            card = self.add_card('company', title='Company')
            card.add_entry(value='Warning No Companies in the system', label='Warning')
        else:
            card = self.add_card('company', title='Company', details_object=company, show_created_modified_dates=True)
            card.add_rows(['name', 'active'],
                          [{'field': 'company_category__name', 'label': 'category'}],
                          'importance')

        self.add_card_group('welcome', 'extra', div_css_class='col-6 float-left')
        self.add_card_group('company', div_css_class='col-6 float-right')


