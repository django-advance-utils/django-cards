import json

from ajax_helpers.mixins import AjaxHelpers
from ajax_helpers.utils import random_string
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django_menus.menu import MenuMixin
from django_modals.modals import ModalException

from cards.base import CardBase, CARD_TYPE_STANDARD, CARD_TYPE_HTML
from cards.standard import CardMixin


class CardTreeMixin:
    list_class = 'col-sm-5 col-md-4 col-lg-3 float-left'
    details_class = 'col-sm-7 col-md-8 col-lg-9 float-left'

    list_title = ''
    menu_display = ''
    datatable_model = None
    card_cls = CardBase
    model = None

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
                   'details_button_action_name': 'details_html'}

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

    def split_slug(self, kwargs):
        if 'slug' in kwargs:
            if not hasattr(self, 'slug'):
                self.slug = {}
            if kwargs['slug'] == '-':
                self.slug['pk'] = '-'
            else:
                s = kwargs['slug'].split('-')
                if len(s) == 1:
                    self.slug['pk'] = s[0]
                else:
                    self.slug.update({s[k]: s[k+1] for k in range(0, int(len(s)-1), 2)})
                if 'pk' in self.slug:
                    self.kwargs['pk'] = self.slug['pk']

    def __init__(self):
        super().__init__()
        self.slug = {}
        self.cards = {}

    # noinspection PyMethodMayBeStatic
    def process_slug_kwargs(self):
        return True

    def dispatch(self, request, *args, **kwargs):
        self.split_slug(kwargs)
        if self.process_slug_kwargs():
            # noinspection PyUnresolvedReferences
            return super().dispatch(request, *args, **self.kwargs)
        else:
            raise ModalException('User does not have permission')

    def get_details_object(self, pk):
        if self.model is None:
            return pk
        return get_object_or_404(self.model, pk=pk)

    def get_details_menu(self, details_object):
        return []

    def get_details_title(self, details_object):
        return 'Details'

    def get_group_type(self, details_object):
        return CARD_TYPE_STANDARD

    def get_list_menu(self):
        return []

    def get_card_template(self):
        return None

    def get_card_footer(self, details_object):
        return ''

    def get_show_created_modified_dates(self, details_object):
        return True

    def get_extra_card_kwargs(self, details_object):
        return {}

    def button_details_html(self, extra_card_context=None, **kwargs):
        details_object = self.get_details_object(pk=kwargs['entry_id'])

        if hasattr(self, 'setup_details_cards'):
            self.setup_details_cards(details_object=details_object)
        else:
            self.add_main_card(details_object=details_object, extra_card_context=extra_card_context)

        data = self._render_cards()
        return self.command_response('html', selector='#details_card', html=data)

    def add_main_card(self, details_object, extra_card_context=None, code='main'):
        if extra_card_context is None:
            extra_card_context = {}
        menu = self.get_details_menu(details_object=details_object)
        title = self.get_details_title(details_object=details_object)
        group_type = self.get_group_type(details_object=details_object)
        footer = self.get_card_footer(details_object=details_object)
        show_created_modified_dates = self.get_show_created_modified_dates(details_object=details_object)
        extra_card_kwargs = self.get_extra_card_kwargs(details_object=details_object)
        template_name = self.get_card_template()
        card = self.add_detail_card(title=title,
                                    code=code,
                                    details_object=details_object,
                                    menu=menu,
                                    show_created_modified_dates=show_created_modified_dates,
                                    group_type=group_type,
                                    footer=footer,
                                    datatable_model=self.datatable_model,
                                    extra_card_context=extra_card_context,
                                    template_name=template_name,
                                    **extra_card_kwargs)
        return card

    def add_detail_card(self, code=None, details_object=None, title=None, menu=None, template_name=None,
                        group_type=CARD_TYPE_STANDARD, show_created_modified_dates=False,
                        footer=None, extra_card_context=None, **extra_card_kwargs):
        if code is None:
            code = random_string()

        card = self.card_cls(request=self.request,
                             view=self,
                             code=code,
                             title=title,
                             menu=menu,
                             show_created_modified_dates=show_created_modified_dates,
                             footer=footer,
                             group_type=group_type,
                             details_object=details_object,
                             extra_card_context=extra_card_context,
                             template_name=template_name,
                             **extra_card_kwargs)

        self.cards[code] = card
        if group_type == CARD_TYPE_STANDARD:
            self.get_details_data(card=card, details_object=details_object)
        return card

    def add_html_group(self, context_template_name, context, **kwargs):
        html = render_to_string(context_template_name, context)
        self.add_detail_card(group_type=CARD_TYPE_HTML,
                             html=html,
                             **kwargs)

    def _render_cards(self):
        data = ""
        for card_key, card in self.cards.items():
            data += card.render()
        return data

    def get_details_data(self, card, details_object):
        pass

    def get_tree_data(self, selected_id):
        return []


class CardTree(AjaxHelpers, MenuMixin, CardMixin, CardTreeMixin):
    pass
