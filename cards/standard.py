from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from cards.base import CardBase


class Card(CardBase):
    template_types = {'default': 'cards/standard/default.html'}

    def __init__(self, request, details_object=None, title=None, menu=None,
                 group_type=CardBase.GROUP_TYPE_STANDARD, show_created_modified_dates=False):
        super().__init__()
        self.details_object = details_object
        self.request = request
        self.group_type = group_type
        self.show_created_modified_dates = show_created_modified_dates

        created_modified_dates = self.get_created_modified_dates(details_object=details_object)
        self.add_detail_group(code=None,
                              title=title,
                              menu=menu,
                              created_modified_dates=created_modified_dates,
                              group_type=group_type,
                              details_object=details_object)

    def render(self, template_name='default'):
        template = self.template_types.get(template_name, template_name)
        self.get_details_data(details_object=self.details_object, group_type=self.group_type)
        data = render_to_string(template, {'groups': self.detail_groups,
                                           'request': self.request,
                                           'group_types': {'standard': self.GROUP_TYPE_STANDARD,
                                                           'datatable': self.GROUP_TYPE_DATATABLE,
                                                           'ordered_datatable': self.GROUP_TYPE_ORDERED_DATATABLE,
                                                           'html': self.GROUP_TYPE_HTML}})
        return mark_safe(data)

    def get_created_modified_dates(self, details_object):
        if self.show_created_modified_dates:
            return super().get_created_modified_dates(details_object=details_object)
        return None


class CardMixin:

    card_cls = Card

    def add_card_group(self, *args, div_css_class):
        cards = [self.cards[card] for card in args]
        self.card_groups.append({'div_css_class': div_css_class, 'cards': cards})

    def add_card(self, card_name, **kwargs):
        request = getattr(self, 'request', None)

        if 'details_object' in kwargs:
            self.cards[card_name] = self.card_cls(request=request, **kwargs)
        else:
            details_object = getattr(self, 'object', None)
            self.cards[card_name] = self.card_cls(request=request, details_object=details_object, **kwargs)

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cards = {}
        self.card_groups = []
