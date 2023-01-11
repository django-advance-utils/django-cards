from ajax_helpers.mixins import AjaxHelpers
from django.utils.safestring import mark_safe
from django_menus.menu import MenuMixin

from cards.base import CARD_TYPE_HTML
from cards.card_list.base import CardListBaseMixin
from cards.standard import CardMixin


class CardListMixin(CardListBaseMixin):
    list_class = 'col-sm-5 col-md-4 col-lg-3 float-left'
    details_class = 'col-sm-7 col-md-8 col-lg-9 float-left'

    list_type = None
    list_title = ''
    menu_display = ''

    model = None

    def add_list_card(self):
        list_menu = self.get_list_menu()
        selected_id = self.slug.get('pk')
        self.display_list_entries()
        if (not selected_id or selected_id == '-') and self.list_entries:
            selected_id = self.list_entries[0]['pk']
        elif selected_id == '-':
            selected_id = ''

        if selected_id:
            selected_id = int(selected_id)

        context = {'list_title': self.list_title,
                   'entries': self.list_entries,
                   'selected_id': selected_id,
                   'empty_list_message': self.empty_list_message(),
                   'details_button_action_name': 'details_html',
                   'details_empty_button_action_name': 'empty_details_html'}

        self.add_card('list_card',
                      title=self.list_title,
                      menu=list_menu,
                      group_type=CARD_TYPE_HTML,
                      template_name='list_selection',
                      extra_card_context=context)

    def setup_cards(self):
        self.add_list_card()
        self.add_card('details_card',
                      group_type=CARD_TYPE_HTML,
                      template_name='blank',
                      html='')

        self.add_card_group('list_card', div_css_class=self.list_class)
        self.add_card_group('details_card', div_css_class=self.details_class)

    def empty_list_message(self):
        list_type = self.list_type if self.list_type is not None else self.list_title
        return f'No {list_type} setup yet!'

    def empty_details_message(self):
        list_type = self.list_type if self.list_type is not None else self.list_title
        return f'No {list_type} setup yet!'

    def get_empty_details_title(self):
        return 'Details'

    def get_empty_details_menu(self):
        return []

    def button_empty_details_html(self, extra_card_context=None, **kwargs):
        card = self.add_card(title=self.get_empty_details_title(),
                             template_name='message',
                             menu=self.get_empty_details_menu(),
                             extra_card_context={'message': self.empty_details_message()})
        return self.command_response('html', selector='#details_card', html=card.render())

    def __init__(self):
        self.list_entries = []
        super().__init__()

    def add_list_entry(self, pk, name, colour=None, row_class=None):
        self.list_entries.append({'pk': pk, 'name': mark_safe(name),
                                  'colour': colour, 'class': row_class if row_class else ''})

    def get_list_entry_name(self, entry_object):
        return entry_object.name

    def get_list_colour(self, entry_object):
        return None

    def get_list_entries(self):
        return self.model.objects.all()

    def display_list_entries(self):
        for entry_object in self.get_list_entries():
            name = self.get_list_entry_name(entry_object=entry_object)
            colour = self.get_list_colour(entry_object=entry_object)
            self.add_list_entry(pk=entry_object.pk,
                                name=name,
                                colour=colour)


class CardList(AjaxHelpers, MenuMixin, CardMixin, CardListMixin):
    pass
