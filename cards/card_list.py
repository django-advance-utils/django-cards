from ajax_helpers.mixins import AjaxHelpers
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView
from django_menus.menu import MenuMixin
from django_modals.modals import ModalException

from cards.base import CardBase


class CardListMixin(CardBase, TemplateView):
    template_name = 'cards/list/list.html'
    list_class = 'col-sm-5 col-md-4 col-lg-3 float-left'
    details_class = 'col-sm-7 col-md-8 col-lg-9 float-left'

    list_type = None
    list_title = ''
    menu_display = ''

    model = None

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
        self.list_entries = []
        super().__init__()
        self.slug = {}

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

    def add_list_entry(self, pk, name, colour=None, row_class=None):
        self.list_entries.append({'pk': pk, 'name': mark_safe(name),
                                  'colour': colour, 'class': row_class if row_class else ''})

    def get_list_entry_name(self, entry_object):
        return entry_object.name

    def get_list_entries(self):
        return self.model.objects.all()

    def display_list_entries(self):
        for entry_object in self.get_list_entries():
            name = self.get_list_entry_name(entry_object=entry_object)
            self.add_list_entry(pk=entry_object.pk,
                                name=name)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['details_class'] = self.details_class
        context['list_class'] = self.list_class
        context['list_title'] = self.list_title
        context['list_type'] = self.list_type if self.list_type is not None else self.list_title

        self.display_list_entries()

        context['entries'] = self.list_entries
        selected_id = self.slug.get('pk')
        if (not selected_id or selected_id == '-') and self.list_entries:
            selected_id = self.list_entries[0]['pk']

        if selected_id:
            selected_id = int(selected_id)
        context['selected_id'] = selected_id
        return context

    def setup_menu(self):
        super().setup_menu()
        list_menu = self.get_list_menu()
        if list_menu:
            self.add_menu('list_menu', 'button_group').add_items(*list_menu)

    def get_details_object(self, pk):
        return get_object_or_404(self.model, pk=pk)

    def get_list_menu(self):
        return []

    def set_card_template(self, template_name):
        self.detail_cards[self.current_card]['template_name'] = template_name

    def button_details_html(self, extra_card_context=None, **kwargs):
        details_object = self.get_details_object(pk=kwargs['entry_id'])

        menu = self.get_details_menu(details_object=details_object)
        title = self.get_details_title(details_object=details_object)

        group_type = self.get_group_type(details_object=details_object)
        created_modified_dates = self.get_created_modified_dates(details_object=details_object)
        self.add_detail_card(code=None,
                             title=title,
                             menu=menu,
                             created_modified_dates=created_modified_dates,
                             group_type=group_type,
                             details_object=details_object,
                             datatable_model=self.datatable_model,
                             extra_card_context=extra_card_context)

        self.set_card_template('default')

        self.get_details_data(details_object=details_object, group_type=group_type)

        # data = render_to_string(self.details_template_name, {'groups': self.detail_groups,
        #                                                      'request': self.request,
        #                                                      'group_types': {'standard': self.GROUP_TYPE_STANDARD,
        #                                                                      'datatable': self.GROUP_TYPE_DATATABLE,
        #                                                                      'html': self.GROUP_TYPE_HTML}})

        data = self._render_cards()
        return self.command_response('html', selector='#details_card', html=data)

    def add_html_group(self, code, title, template_name, context, extra_card_context=None, menu=None):
        self.add_detail_card(code=code,
                             title=title,
                             menu=menu,
                             group_type=self.CARD_TYPE_HTML,
                             extra_card_context=extra_card_context,
                             template_name=self.template_name)
        html = render_to_string(template_name, context)
        self.detail_cards[code]['html'] = html


class CardList(AjaxHelpers, MenuMixin, CardListMixin):
    pass
