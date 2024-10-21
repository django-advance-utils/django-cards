from django.forms import CharField, FileField, BooleanField
from django.views.generic import TemplateView
from django_menus.menu import MenuItem
from django_modals.forms import CrispyForm
from django_modals.modals import Modal, FormModal, ModelFormModal
from django_modals.processes import PERMISSION_OFF
from django_modals.widgets.widgets import Toggle

from cards.standard import CardMixin
from cards_examples.models import Company
from cards_examples.views.base import MainMenu


class ModalExampleIndex(MainMenu, CardMixin, TemplateView):
    model = Company
    template_name = 'cards_examples/modal.html'

    def setup_menu(self):
        super().setup_menu()
        self.simple_modals()
        self.form_modals()

    def simple_modals(self):
        self.add_menu(menu_name='simple_modals', menu_type='buttons').add_items(
            MenuItem(url='cards_examples:simple_modal', menu_display='Simple Modal'))

    def form_modals(self):
        self.add_menu(menu_name='form_modals', menu_type='buttons').add_items(
            MenuItem(url='cards_examples:form_modal',
                     menu_display='Form Modal'),
            MenuItem(url='cards_examples:company_modal',
                     menu_display='Model Form Modal',
                     url_kwargs={'slug':'1'}))


class CardModalMixin(CardMixin, Modal):
    card_methods = []

    def main_card(self, *args, **kwargs):
        pass

    def get_cards(self):
        if len(self.card_methods) > 1:
            cards = [getattr(self, card_method)() for card_method in self.card_methods]
            return cards
        else:
            return None

    def render_cards(self):
        rendered_card_groups = {}
        for code, card_groups in self.card_groups.items():
            rendered_card_groups[code] = self.render_card_groups(card_groups)
        return rendered_card_groups['main']

    # noinspection PyUnresolvedReferences
    def modal_content(self):
        cards = self.get_cards()
        if cards is not None:
            self.add_card_group(*cards)
            return self.render_cards()
        if len(self.card_groups) > 0:
            return self.render_cards()
        else:
            card = self.main_card()
            return card.render()


class SimpleMainCard(CardModalMixin):
    def main_card(self):
        card = self.add_card()
        card.add_entry(label='Label', value='Value')
        card.add_entry(label='A Simple', value='Main Card')
        return card


class MultipleCards(CardModalMixin):
    card_methods = ['example_card_one', 'example_card_two', 'example_card_three']

    def example_card_one(self):
        card = self.add_card()
        card.add_entry(label='Label', value='Value')
        card.add_entry(label='Example Card', value='1')
        return card

    def example_card_two(self):
        card = self.add_card()
        card.add_entry(label='Label', value='Value')
        card.add_entry(label='Example Card', value='2')
        return card

    def example_card_three(self):
        card = self.add_card()
        card.add_entry(label='Label', value='Value')
        card.add_entry(label='Example Card', value='3')
        return card


class MultipleCardsWithSetup(CardModalMixin):
    def setup_cards(self):
        left_cards, right_cards = self.get_all_cards()
        self.add_card_group(*left_cards, div_css_class='col-6 float-left')
        self.add_card_group(*right_cards, div_css_class='col-6 float-right')

    def get_all_cards(self):
        main_card = self.main_card()
        example_card_one = self.example_card_one()
        example_card_two = self.example_card_two()
        example_card_three = self.example_card_three()
        return [main_card, example_card_one], [example_card_two, example_card_three]

    def main_card(self):
        card = self.add_card()
        card.add_entry(label='Label', value='Value')
        card.add_entry(label='Main', value='Main Value')
        return card

    def example_card_one(self):
        card = self.add_card()
        card.add_entry(label='Label', value='Value')
        card.add_entry(label='Example Card', value='1')
        return card

    def example_card_two(self):
        card = self.add_card()
        card.add_entry(label='Label', value='Value')
        card.add_entry(label='Example Card', value='2')
        return card

    def example_card_three(self):
        card = self.add_card()
        card.add_entry(label='Label', value='Value')
        card.add_entry(label='Example Card', value='3')
        return card


class CardFormMixin(CardMixin):
    # noinspection PyUnresolvedReferences
    def form_setup(self, form, *args, **kwargs):
        return self.add_form_card(form)

    def card_object(self):
        return None

    def add_form_card(self, form):
        card = self.add_card(template_name='modal',
                             extra_card_context={'card_body_css_class': 'pb-1'},
                             details_object=self.card_object(),
                             form=form)
        self.add_form_card_fields(card)
        return card

    def add_form_card_fields(self, card):
        raise NotImplementedError('Subclasses must implement this method.')


class CardFormModalMixin(CardFormMixin, FormModal):
    pass


class CardModelFormModalMixin(CardFormMixin, ModelFormModal):
    card_fields = None
    def card_object(self):
        return self.model.objects.get(id=self.slug['pk'])

    def add_form_card(self, form):
        card = self.add_card(template_name='modal',
                             extra_card_context={'card_body_css_class': 'pb-1'},
                             details_object=self.card_object(),
                             form=form)
        if self.card_fields is not None:
            card.add_rows(*self.card_fields)
        self.add_form_card_fields(card)
        return card


class ModalCompanyForm(CardModelFormModalMixin):
    model = Company
    permission_delete = PERMISSION_OFF
    card_fields = ['name', 'active']

    def form_setup(self, form, *args, **kwargs):
        form.fields['name'] = CharField()
        return super().form_setup(form, *args, **kwargs)

    def add_form_card_fields(self, card):
        card.add_entry(value=['a', 'b'], label='test', html_override="<b>%1%</b>")
        card.add_entry(form_field='name')
        card.add_entry(field='sectors')


class ExampleFormModal(CardFormModalMixin):
    form_class = CrispyForm

    def card_object(self):
        return Company.objects.first()

    @property
    def modal_title(self):
        return 'Django Forms Example'

    def form_setup(self, form, *args, **kwargs):
        form.fields['name'] = CharField()
        form.fields['file'] = FileField()
        form.fields['toggle'] = BooleanField(widget=Toggle)
        return super().form_setup(form, *args, **kwargs)

    def add_form_card_fields(self, card):
        card.add_entry(form_field='toggle')
        card.add_rows(['name', 'active'],
                      [{'field': 'company_category__name', 'label': 'category'}],
                      'importance',
                      {'field': 'importance'},
                      {'field': 'get_display_name', 'label': 'Display Name'})
        card.add_entry(form_field='file')
        card.add_entry(value=['a', 'b'], label='test', html_override="<b>%1%</b>")
        card.add_entry(form_field='name')
        card.add_entry(field='sectors')

    def form_valid(self, form):
        name = form.cleaned_data['name']
        return self.command_response('message', text=name)
