import json

from ajax_helpers.utils import is_ajax
from django.http import HttpResponse
from django.template.loader import render_to_string

from cards.base import CardBase, CARD_TYPE_HTML


class CardMixin:

    card_cls = CardBase

    def __init__(self, *args, **kwargs):
        self.tables = {}
        self.cards = {}
        self.card_groups = {}
        super().__init__(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.POST.get('datatable_data'):
            table_id = request.POST['table_id']

            field_setup_table_field = f'setup_table_{table_id}'
            if hasattr(self, field_setup_table_field):
                self.setup_datatable_cards()
                table = self.tables[table_id]
                field_query = f'get_{table_id}_query'
                if hasattr(self, field_query):
                    results = getattr(self, field_query)(table, **kwargs)
                else:
                    results = table.get_query(**kwargs)
                table_data = table.get_json(request, results)
                return HttpResponse(table_data, content_type='application/json')
        # noinspection PyUnresolvedReferences
        if hasattr(super(), 'post'):
            # noinspection PyUnresolvedReferences
            return super().post(request, *args, **kwargs)
        elif is_ajax(request) and request.content_type == 'application/json':
            response = json.loads(request.body)
            raise Exception(f'May need to use AjaxHelpers Mixin or'
                            f' add one of these \n{", ".join(response.keys())}\nto ajax_commands ')

    def add_card_group(self, *args, div_css_class='', div_css='', error_if_not_found=True, group_code='main'):
        cards = []
        for card in args:
            if isinstance(card, str):
                if error_if_not_found or card in self.cards:
                    cards.append(self.cards[card])
            else:
                cards.append(card)


        if group_code not in self.card_groups:
            self.card_groups[group_code] = []

        self.card_groups[group_code].append({'div_css_class': div_css_class,
                                             'div_css': div_css,
                                             'cards': cards})

    def add_card(self, card_name=None, **kwargs):
        request = getattr(self, 'request', None)

        if 'details_object' in kwargs:
            card = self.card_cls(request=request,
                                 view=self,
                                 code=card_name,
                                 **kwargs)
        else:
            details_object = getattr(self, 'object', None)
            card = self.card_cls(request=request,
                                 view=self,
                                 code=card_name,
                                 details_object=details_object,
                                 **kwargs)
        if card_name is not None:
            self.cards[card_name] = card
        return card

    def get_context_data(self, **kwargs):
        self.setup_datatable_cards()
        self.setup_cards()
        super_context = getattr(super(), 'get_context_data')
        if super_context and callable(super_context):
            context = super_context(**kwargs)
        else:
            context = {}
        context['cards'] = self.cards
        rendered_card_groups = {}
        for code, card_groups in self.card_groups.items():
            if len(card_groups) > 0:
                rendered_card_groups[code] = self.render_card_groups(card_groups)

        context['card_groups'] = rendered_card_groups
        return context

    def render_card_groups(self, card_groups):
        return render_to_string('cards/groups/groups.html', context={'groups': card_groups})

    def setup_cards(self):
        if hasattr(super(), 'setup_cards'):
            super().setup_cards()

    def setup_datatable_cards(self):
        if hasattr(super(), 'setup_datatable_cards'):
            super().setup_datatable_cards()

    def add_html_card(self, context_template_name, context=None, is_empty=False, **kwargs):
        if not is_empty:
            if context is None:
                context = {}
            if 'details_object' in kwargs:
                context['object'] = kwargs['details_object']

            html = render_to_string(context_template_name, context)
        else:
            html = ''

        return self.add_card(group_type=CARD_TYPE_HTML, html=html, is_empty=is_empty, **kwargs)

    def row_edit(self, **kwargs):
        row_data = json.loads(kwargs.pop('row_data'))
        self.setup_datatable_cards()
        table_id = kwargs['table_id']
        table = self.tables[table_id]
        row_object = table.model.objects.get(pk=kwargs['row_no'][1:])
        field_setup_table_field = f'setup_table_{table_id}'
        if hasattr(self, field_setup_table_field):
            getattr(self, field_setup_table_field)(table=table, details_object=self.cards[table_id].details_object)
        table.columns[kwargs['changed'][0]].alter_object(row_object, row_data[kwargs['changed'][0]])
        return table.refresh_row(self.request, kwargs['row_no'])


