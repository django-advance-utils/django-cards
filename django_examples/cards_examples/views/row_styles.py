from cards_examples.views.base import MainMenu
from django.views.generic import TemplateView
from django_menus.menu import MenuItem
from html_classes.html import HtmlElement, HtmlDiv

from cards.standard import CardMixin
from cards_examples.models import Person


class RowStyleExampleIndex(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        no_db_card = self.add_row_style_no_db()
        self.add_card_group(no_db_card, div_css_class='col-6 float-left')

        db_card = self.add_row_style_with_db()
        self.add_card_group(db_card, div_css_class='col-6 float-right')

    def add_row_style_no_db(self):
        card = self.add_card(title='Row Style Examples no DB')

        card.add_row_style('test', html=HtmlDiv([HtmlElement(element='span',
                                                             contents=[HtmlElement(element='h4', contents='{label}')]),
                                                 HtmlElement(element='span', contents='{value}')]))

        card.add_row_style('test2', html=HtmlDiv([HtmlElement(element='span',
                                                              contents=[HtmlElement(element='h4', contents='{label}')]),
                                                  HtmlElement(element='span', contents='{value} - {test}')]))

        card.add_row_style('multi_value', html=HtmlDiv([HtmlElement(element='span',
                                                                    contents=[
                                                                        HtmlElement(element='h4', contents='{label}')]),
                                                        HtmlElement(element='span', contents='{value[v1]} - {value[v2]}')]))

        card.add_entry(label='No Row Style', value='Row Style line')
        card.add_entry(value='Row Style line', label='Has Row Style', row_style='test')
        card.add_entry(value='value 1', label='Has Row Style', test='fred', row_style='test2')
        card.add_entry(value={'v1': 'foo', 'v2': 'bar'}, label='Has Row Style', row_style='multi_value')
        return card

    def add_row_style_with_db(self):
        person = Person.objects.first()
        if person is None:
            card = self.add_card('person', title='Person')
            card.add_entry(value='Warning No People in the system', label=None,
                           html_override='<div class="alert alert-warning">%1%</div>')
        else:
            card = self.add_card('person',
                                 title='Person', details_object=person)
            card.add_row_style('test', html=HtmlDiv([HtmlElement(element='span',
                                                                 contents=[
                                                                     HtmlElement(element='h1', contents='{label}')]),
                                                     HtmlElement(element='span', contents='{value}')]),
                               is_default=True)

            card.add_row_style('with_menu', html=HtmlDiv([HtmlElement(element='span',
                                                                      contents=[
                                                                          HtmlElement(element='h5',
                                                                                      contents='{label}')]),
                                                          HtmlElement(element='span', contents='{value}'),
                                                          HtmlElement(element='span', contents='{menu}')]))

            card.add_row_style('multi',
                               html=HtmlDiv([HtmlElement(element='span',
                                                         contents=[
                                                             HtmlElement(element='h3', contents='{label}')]),
                                             HtmlElement(element='span', contents='{value[0]} -- {value[1]}')]))

            card.add_row_style('crash', html=HtmlDiv([HtmlElement(element='span',
                                                                 contents=[
                                                                     HtmlElement(element='h1', contents='{label}')]),
                                                     HtmlElement(element='span', contents='{foo}')]))


            card.add_entry(field=['first_name', 'surname'], label='Names', row_style='multi')

            menu = [MenuItem('cards_examples:hello_modal', menu_display='',
                             font_awesome='fas fa-edit', css_classes='btn btn-link')]

            card.add_rows('is_active',
                          {'field': ['first_name', 'surname'], 'label': 'Names', 'row_style': 'multi'},
                          {'field': 'first_name', 'menu': menu, 'row_style': 'with_menu'},
                          {'field': 'first_name', 'menu': menu, 'row_style': 'crash'},)

        return card


