from django_modals.modals import FormModal, ModelFormModal, Modal

from cards.standard import CardMixin


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
            return self.main_card().render()


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
