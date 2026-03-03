import datetime

from cards_examples.models import Company, Person
from cards_examples.views.base import MainMenu
from django.utils import timezone
from django.views.generic import TemplateView

from cards.standard import CardMixin


class NewFeaturesIndex(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_tooltip_card()
        self.add_value_link_card()
        self.add_css_class_method_card()
        self.add_company_features_card()
        self.add_badge_card()
        self.add_icon_card()
        self.add_copy_truncate_card()
        self.add_reload_card()
        self.add_prefix_suffix_card()
        self.add_placeholder_card()
        self.add_status_dot_card()
        self.add_progress_bar_card()
        self.add_image_card()
        self.add_timestamp_card()

        self.add_card_group('tooltip', 'value_link',
                            div_css_class='col-6 float-left',
                            div_id='left-column',
                            group_title='Tooltip & Link Examples')
        self.add_card_group('css_class_method', 'company_features',
                            div_css_class='col-6 float-right',
                            div_id='right-column',
                            group_title='CSS & Company Examples',
                            script='console.log("New features examples loaded");')
        self.add_card_group('badge', 'icon', 'copy_truncate',
                            div_css_class='col-12')
        self.add_card_group('reload',
                            div_css_class='col-12')
        self.add_card_group('prefix_suffix', 'placeholder', 'status_dot',
                            div_css_class='col-12')
        self.add_card_group('progress_bar', 'image', 'timestamp',
                            div_css_class='col-12')

    def add_tooltip_card(self):
        card = self.add_card('tooltip', title='Tooltip Examples')
        card.add_entry(value='Hover over me',
                       label='With tooltip',
                       tooltip='This is a Bootstrap tooltip')
        card.add_entry(value='No tooltip here',
                       label='Without tooltip')
        card.add_entry(value='Check the tooltip',
                       label='Status info',
                       tooltip='Last updated 2 hours ago')

    def add_value_link_card(self):
        card = self.add_card('value_link', title='Value Link Examples')
        card.add_entry(value='https://example.com',
                       label='Website',
                       value_link='https://example.com')
        card.add_entry(value='user@example.com',
                       label='Email',
                       value_link='mailto:user@example.com')
        card.add_entry(value='Click the whole row',
                       label='Row link',
                       link='https://example.com')
        card.add_entry(value='Only value is linked',
                       label='Value link',
                       value_link='https://example.com',
                       tooltip='Click the value text')

    def add_css_class_method_card(self):
        card = self.add_card('css_class_method', title='CSS Class Method Examples')
        card.add_entry(value=150,
                       label='Positive balance',
                       css_class_method=lambda v: 'text-success' if v >= 0 else 'text-danger')
        card.add_entry(value=-42,
                       label='Negative balance',
                       css_class_method=lambda v: 'text-success' if v >= 0 else 'text-danger')
        card.add_entry(value=0,
                       label='Zero balance',
                       css_class_method=lambda v: 'text-success' if v >= 0 else 'text-danger')
        card.add_entry(value='HIGH',
                       label='Priority',
                       css_class_method=lambda v: {
                           'HIGH': 'text-danger fw-bold',
                           'MEDIUM': 'text-warning',
                           'LOW': 'text-success',
                       }.get(v, ''))

    def add_company_features_card(self):
        company = Company.objects.first()
        if company is None:
            card = self.add_card('company_features', title='Company (New Features)')
            card.add_entry(value='No companies in the system',
                           label=None,
                           html_override='<div class="alert alert-warning">%1%</div>')
        else:
            card = self.add_card('company_features',
                                 title='Company (New Features)',
                                 details_object=company)
            card.add_entry(field='name',
                           tooltip='The registered company name')
            card.add_entry(field='importance',
                           tooltip='1 = low, 10 = high',
                           css_class_method=lambda v: 'text-danger fw-bold' if v and v >= 8 else '')
            card.add_entry(field='active',
                           tooltip='Whether the company is currently active')


    def add_badge_card(self):
        card = self.add_card('badge', title='Badge Examples',
                             header_icon='fas fa-tags',
                             header_css_class='bg-primary text-white')
        card.add_entry(value='Active',
                       label='Status',
                       badge=True)
        card.add_entry(value='Overdue',
                       label='Payment',
                       badge='bg-danger')
        card.add_entry(value='Pending',
                       label='Review',
                       badge='bg-warning text-dark')
        card.add_entry(value='Complete',
                       label='Task',
                       badge='bg-success')

    def add_icon_card(self):
        card = self.add_card('icon', title='Icon Examples',
                             header_icon='fas fa-icons')
        card.add_entry(value='user@example.com',
                       label='Email',
                       icon='fas fa-envelope')
        card.add_entry(value='+1 555-0123',
                       label='Phone',
                       icon='fas fa-phone')
        card.add_entry(value='New York, USA',
                       label='Location',
                       icon='fas fa-map-marker-alt')
        card.add_entry(value='Premium',
                       label='Plan',
                       icon='fas fa-crown',
                       badge='bg-warning text-dark')

    def add_copy_truncate_card(self):
        card = self.add_card('copy_truncate', title='Copy & Truncate Examples',
                             header_icon='fas fa-clipboard',
                             header_css_class='bg-dark text-white')
        card.add_entry(value='sk-abc123def456ghi789',
                       label='API Key',
                       copy_to_clipboard=True)
        card.add_entry(value='user@example.com',
                       label='Email',
                       icon='fas fa-envelope',
                       copy_to_clipboard=True)
        card.add_entry(value='This is a very long description that should be truncated to a reasonable length for display purposes in the card UI',
                       label='Description',
                       truncate=50)
        card.add_entry(value='Short text',
                       label='No truncation',
                       truncate=50)

    def add_reload_card(self):
        card = self.add_card('reload', title='AJAX Reload Examples',
                             header_icon='fas fa-sync-alt',
                             ajax_reload=True)
        card.add_entry(value=datetime.datetime.now().strftime('%H:%M:%S'),
                       label='Last loaded',
                       icon='fas fa-clock')
        card.add_entry(value='Click the reload button in the header to refresh this card',
                       label='Manual reload')
        card.add_entry(value='Use ajax_reload=True on any card',
                       label='Usage',
                       icon='fas fa-code')

    def add_prefix_suffix_card(self):
        card = self.add_card('prefix_suffix', title='Prefix & Suffix Examples',
                             header_icon='fas fa-text-width')
        card.add_entry(value='1,250.00', label='Price', prefix='$')
        card.add_entry(value='75', label='Completion', suffix='%')
        card.add_entry(value='25.5', label='Temperature', suffix=' °C')
        card.add_entry(value='100', label='Full price', prefix='$', suffix=' USD')

    def add_placeholder_card(self):
        card = self.add_card('placeholder', title='Placeholder Examples',
                             header_icon='fas fa-eye-slash')
        card.add_entry(value=None, label='Notes', placeholder=True)
        card.add_entry(value=None, label='Bio', placeholder='Not provided')
        card.add_entry(value='Has a value', label='Name', placeholder=True)
        card.add_entry(value='', label='Empty field', placeholder='No data available')

    def add_status_dot_card(self):
        card = self.add_card('status_dot', title='Status Dot Examples',
                             header_icon='fas fa-circle')
        card.add_entry(value='Active', label='Status', status_dot='green')
        card.add_entry(value='Warning', label='Service', status_dot='orange')
        card.add_entry(value='Error', label='Database', status_dot='red')
        card.add_entry(value='Inactive', label='Backup', status_dot='gray')

    def add_progress_bar_card(self):
        card = self.add_card('progress_bar', title='Progress Bar Examples',
                             header_icon='fas fa-tasks')
        card.add_entry(value=75, label='Completion', progress_bar=True)
        card.add_entry(value=90, label='Disk Usage', progress_bar='bg-danger')
        card.add_entry(value=45, label='Upload', progress_bar='bg-info')
        card.add_entry(value=100, label='Done', progress_bar='bg-success')

    def add_image_card(self):
        card = self.add_card('image', title='Image Examples',
                             header_icon='fas fa-image')
        card.add_entry(value='https://placehold.co/100x40/007bff/ffffff?text=Logo',
                       label='Logo', image=True)
        card.add_entry(value='https://placehold.co/100x60/28a745/ffffff?text=Avatar',
                       label='Avatar', image='60px')

    def add_timestamp_card(self):
        card = self.add_card('timestamp', title='Timestamp Examples',
                             header_icon='fas fa-clock')
        card.add_entry(value=timezone.now() - datetime.timedelta(hours=2),
                       label='Created', timestamp=True)
        card.add_entry(value=timezone.now() - datetime.timedelta(days=3),
                       label='Last login', timestamp=True)
        card.add_entry(value=datetime.date.today() - datetime.timedelta(days=30),
                       label='Start date', timestamp=True)


class NewFeaturesTableIndex(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_table_tooltip_card()
        self.add_table_value_link_card()
        self.add_table_badge_icon_card()
        self.add_table_copy_truncate_card()
        self.add_table_new_features_card()

        self.add_card_group('table_tooltip',
                            div_css_class='col-6 float-left',
                            div_id='table-left',
                            group_title='Table Tooltip & Link')
        self.add_card_group('table_value_link',
                            div_css_class='col-6 float-right',
                            div_id='table-right')
        self.add_card_group('table_badge_icon', 'table_copy_truncate',
                            div_css_class='col-12')
        self.add_card_group('table_new_features',
                            div_css_class='col-12')

    def add_table_tooltip_card(self):
        card = self.add_card('table_tooltip',
                             title='Table Tooltip Examples',
                             template_name='table',
                             extra_card_context={'table_css_class': 'table table-bordered'})
        card.add_entry(value='Hover me',
                       label='With tooltip',
                       tooltip='Tooltip on a table cell')
        card.add_entry(value='No tooltip',
                       label='Without tooltip')
        card.add_entry(value='Status OK',
                       label='Status',
                       tooltip='All systems operational',
                       css_class_method=lambda v: 'text-success fw-bold')

    def add_table_value_link_card(self):
        card = self.add_card('table_value_link',
                             title='Table Value Link Examples',
                             template_name='table',
                             extra_card_context={'table_css_class': 'table table-bordered'})
        card.add_entry(value='https://example.com',
                       label='Website',
                       value_link='https://example.com')
        card.add_entry(value='admin@example.com',
                       label='Contact',
                       value_link='mailto:admin@example.com',
                       tooltip='Click to send email')

    def add_table_badge_icon_card(self):
        card = self.add_card('table_badge_icon',
                             title='Table Badge & Icon Examples',
                             template_name='table',
                             header_icon='fas fa-table',
                             header_css_class='bg-info text-white',
                             extra_card_context={'table_css_class': 'table table-bordered'})
        card.add_entry(value='Active',
                       label='Status',
                       badge=True,
                       icon='fas fa-circle')
        card.add_entry(value='Overdue',
                       label='Payment',
                       badge='bg-danger',
                       icon='fas fa-exclamation-triangle')
        card.add_entry(value='user@example.com',
                       label='Email',
                       icon='fas fa-envelope')

    def add_table_copy_truncate_card(self):
        card = self.add_card('table_copy_truncate',
                             title='Table Copy & Truncate Examples',
                             template_name='table',
                             header_icon='fas fa-clipboard',
                             extra_card_context={'table_css_class': 'table table-bordered'})
        card.add_entry(value='sk-abc123def456ghi789',
                       label='API Key',
                       copy_to_clipboard=True)
        card.add_entry(value='This is a very long description that should be truncated to a reasonable length for display in table cells',
                       label='Description',
                       truncate=40)

    def add_table_new_features_card(self):
        card = self.add_card('table_new_features',
                             title='Table New Features',
                             template_name='table',
                             header_icon='fas fa-star',
                             extra_card_context={'table_css_class': 'table table-bordered'})
        card.add_entry(value='1,250.00', label='Price', prefix='$')
        card.add_entry(value='75', label='Completion', suffix='%')
        card.add_entry(value='Active', label='Status', status_dot='green')
        card.add_entry(value='Error', label='Service', status_dot='red')
        card.add_entry(value=75, label='Progress', progress_bar=True)
        card.add_entry(value=90, label='Disk', progress_bar='bg-danger')
        card.add_entry(value=None, label='Notes', placeholder=True)
        card.add_entry(value=None, label='Bio', placeholder='Not provided')
        card.add_entry(value=timezone.now() - datetime.timedelta(hours=5),
                       label='Updated', timestamp=True)
