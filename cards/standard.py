from django.http import HttpResponse
from django.template.loader import render_to_string

from cards.base import CardBase, CARD_TYPE_STANDARD


class Card(CardBase):

    def __init__(self, request, code, view=None, details_object=None, title=None, menu=None, template_name='default',
                 group_type=CARD_TYPE_STANDARD,
                 show_created_modified_dates=False, extra_card_context=None, **kwargs):
        super().__init__(view=view)
        self.details_object = details_object
        self.request = request
        self.group_type = group_type
        self.show_created_modified_dates = show_created_modified_dates

        created_modified_dates = self.get_created_modified_dates(details_object=details_object)
        self.add_detail_card(code=code,
                             title=title,
                             menu=menu,
                             created_modified_dates=created_modified_dates,
                             group_type=group_type,
                             details_object=details_object,
                             extra_card_context=extra_card_context,
                             template_name=template_name,
                             **kwargs)

    def render(self):
        self.process_data()
        self.process_data()
        return self._render_cards()

    def get_created_modified_dates(self, details_object):
        if self.show_created_modified_dates:
            return super().get_created_modified_dates(details_object=details_object)
        return None


class CardMixin:

    card_cls = Card

    def __init__(self, *args, **kwargs):
        self.tables = {}
        self.cards = {}
        self.card_groups = []
        super().__init__(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.POST.get('datatable_data'):
            table_id = request.POST['table_id']

            field_setup_table_field = f'setup_table_{table_id}'
            if hasattr(self, field_setup_table_field):
                self.setup_cards()
                card = self.cards[table_id]
                card.current_card = table_id
                card.process_data()
                table = card.tables[request.POST['table_id']]

                field_query = f'get_{table_id}_query'
                if hasattr(self, field_query):
                    results = getattr(self, field_query)(table, **kwargs)
                else:
                    results = table.get_query(**kwargs)
                table_data = table.get_json(request, results)
                return HttpResponse(table_data, content_type='application/json')
        # noinspection PyUnresolvedReferences
        return super().post(request, *args, **kwargs)

    def add_card_group(self, *args, div_css_class):
        cards = [self.cards[card] for card in args]
        self.card_groups.append({'div_css_class': div_css_class, 'cards': cards})

    def add_card(self, card_name, **kwargs):
        request = getattr(self, 'request', None)

        if 'details_object' in kwargs:
            self.cards[card_name] = self.card_cls(request=request,
                                                  view=self,
                                                  code=card_name,
                                                  **kwargs)
        else:
            details_object = getattr(self, 'object', None)
            self.cards[card_name] = self.card_cls(request=request,
                                                  view=self,
                                                  code=card_name,
                                                  details_object=details_object,
                                                  **kwargs)
        return self.cards[card_name]

    def get_context_data(self, **kwargs):
        self.setup_cards()
        super_context = getattr(super(), 'get_context_data')
        if super_context and callable(super_context):
            context = super_context(**kwargs)
        else:
            context = {}
        context['cards'] = self.cards
        if len(self.card_groups) > 0:
            context['card_groups'] = self.render_card_groups()
        return context

    def render_card_groups(self):
        return render_to_string('cards/standard/groups.html', context={'groups': self.card_groups})

    def setup_cards(self):
        return
