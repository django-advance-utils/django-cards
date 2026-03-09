from cards_examples.models import Company, CompanyCategory, Person
from cards_examples.views.base import MainMenu
from django.views.generic import TemplateView

from cards.base import CARD_TYPE_DATATABLE, CARD_TYPE_ACCORDION
from cards.standard import CardMixin


class AccordionExample(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'

    ajax_commands = ['datatable', 'row']

    def setup_datatable_cards(self):
        # Datatable card for the "Companies" panel
        self.add_card('acc_companies',
                      group_type=CARD_TYPE_DATATABLE,
                      datatable_model=Company)

    def setup_table_acc_companies(self, table, details_object):
        table.ajax_data = True
        table.add_columns('id', 'name', 'importance')

    def setup_cards(self):
        # Standard detail card
        detail_card = self.add_card(title='Company Overview')
        detail_card.add_entry(label='Total Companies', value=Company.objects.count())
        detail_card.add_entry(label='Total Categories', value=CompanyCategory.objects.count())
        detail_card.add_entry(label='Total People', value=Person.objects.count())

        # HTML card
        html_card = self.add_card(title='Notes')
        html_card.add_entry(label='Info', value='This is a standard card inside an accordion panel.')
        html_card.add_entry(label='Tip', value='Each panel can contain any card type.')

        companies_card = self.cards['acc_companies']

        self.add_accordion_card(
            card_name='example_accordion',
            title='Accordion Example',
            panels=[
                {'title': 'Overview', 'card': detail_card, 'icon': 'fas fa-chart-bar',
                 'expanded': True},
                {'title': 'Companies', 'card': companies_card, 'icon': 'fas fa-building'},
                {'title': 'Notes', 'card': html_card, 'icon': 'fas fa-sticky-note'},
            ]
        )

        self.add_card_group('example_accordion', div_css_class='col-12 float-right')


class AccordionAjaxExample(MainMenu, CardMixin, TemplateView):
    """Accordion with AJAX-loaded panels."""
    template_name = 'cards_examples/cards.html'

    ajax_commands = ['datatable', 'row']

    def setup_datatable_cards(self):
        self.add_card('acc_ajax_people',
                      group_type=CARD_TYPE_DATATABLE,
                      datatable_model=Person)

    def setup_table_acc_ajax_people(self, table, details_object):
        table.ajax_data = True
        table.add_columns('id', 'first_name', 'surname')

    def setup_cards(self):
        # Eager panel
        summary_card = self.add_card(title='Summary')
        summary_card.add_entry(label='Companies', value=Company.objects.count())
        summary_card.add_entry(label='People', value=Person.objects.count())

        # AJAX-loaded panels
        people_card = self.cards['acc_ajax_people']

        notes_card = self.add_card(title='Lazy Notes')
        notes_card.add_entry(label='Loaded', value='This content was loaded via AJAX when you expanded the panel.')

        self.add_accordion_card(
            card_name='ajax_accordion',
            title='Accordion with AJAX Loading',
            panels=[
                {'title': 'Summary', 'card': summary_card, 'icon': 'fas fa-info-circle',
                 'expanded': True},
                {'title': 'People (AJAX)', 'card': people_card, 'icon': 'fas fa-users',
                 'ajax_load': True},
                {'title': 'Notes (AJAX)', 'card': notes_card, 'icon': 'fas fa-sticky-note',
                 'ajax_load': True},
            ]
        )

        self.add_card_group('ajax_accordion', div_css_class='col-12 float-right')


class AccordionMultiExample(MainMenu, CardMixin, TemplateView):
    """Accordion with multi_open=True so multiple panels can be open at once."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        card1 = self.add_card(title='Panel 1')
        card1.add_entry(label='Description', value='This accordion allows multiple panels open at once.')
        card1.add_entry(label='Style', value='Standard card entries')

        card2 = self.add_card(title='Panel 2')
        card2.add_entry(label='Status', value='Active', badge=True)
        card2.add_entry(label='Progress', value=75, progress_bar=True)

        card3 = self.add_card(title='Panel 3')
        card3.add_entry(label='Note', value='This panel has a custom header style.',)

        self.add_accordion_card(
            card_name='multi_accordion',
            title='Multi-Open Accordion',
            multi_open=True,
            panels=[
                {'title': 'Details', 'card': card1, 'icon': 'fas fa-info-circle', 'expanded': True},
                {'title': 'Status', 'card': card2, 'icon': 'fas fa-tasks', 'expanded': True},
                {'title': 'Custom Header', 'card': card3, 'icon': 'fas fa-paint-brush',
                 'header_css_class': 'bg-light'},
            ]
        )

        self.add_card_group('multi_accordion', div_css_class='col-12 float-right')


class AccordionLayoutExample(MainMenu, CardMixin, TemplateView):
    """Accordion on the left with a detail card on the right."""
    template_name = 'cards_examples/cards.html'

    ajax_commands = ['datatable', 'row']

    def setup_datatable_cards(self):
        self.add_card('acc_layout_people',
                      group_type=CARD_TYPE_DATATABLE,
                      datatable_model=Person)

    def setup_table_acc_layout_people(self, table, details_object):
        table.ajax_data = True
        table.add_columns('id', 'first_name', 'surname')

    def setup_cards(self):
        # Cards for accordion panels
        summary_card = self.add_card(title='Summary')
        summary_card.add_entry(label='Companies', value=Company.objects.count())
        summary_card.add_entry(label='Categories', value=CompanyCategory.objects.count())
        summary_card.add_entry(label='People', value=Person.objects.count())

        people_card = self.cards['acc_layout_people']

        notes_card = self.add_card(title='Notes')
        notes_card.add_entry(label='Tip', value='Accordion on the left, details on the right.')

        self.add_accordion_card(
            card_name='layout_accordion',
            title='Navigation',
            full_height=True,
            panels=[
                {'title': 'Summary', 'card': summary_card, 'icon': 'fas fa-chart-bar',
                 'expanded': True},
                {'title': 'People', 'card': people_card, 'icon': 'fas fa-users'},
                {'title': 'Notes', 'card': notes_card, 'icon': 'fas fa-sticky-note'},
            ]
        )

        # Detail card on the right
        detail_card = self.add_card('right_details', title='Company Details')
        detail_card.add_entry(label='Name', value='Acme Corp')
        detail_card.add_entry(label='Status', value='Active', badge=True)
        detail_card.add_entry(label='Importance', value=8, progress_bar=True)
        detail_card.add_entry(label='Category', value='Technology')
        detail_card.add_entry(label='Founded', value='2005')
        detail_card.add_entry(label='Employees', value=250, number_format=True)

        # Layout: accordion col-4, details col-8
        self.add_card_group('layout_accordion', div_css_class='col-4 float-left')
        self.add_card_group('right_details', div_css_class='col-8 float-left')
