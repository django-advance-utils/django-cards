import datetime

from cards_examples.models import Company, Person
from cards_examples.views.base import MainMenu
from django.utils import timezone
from django.views.generic import TemplateView

from django.utils.html import format_html

from cards.standard import CardMixin, Tile
from django_menus.menu import MenuItem


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
        self.add_help_text_card()
        self.add_boolean_icon_card()
        self.add_popover_card()
        self.add_separator_card()
        self.add_number_format_card()
        self.add_rating_card()

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
                            div_css_class='col-12',
                            div_css='clear:both')
        self.add_card_group('reload',
                            div_css_class='col-12')
        self.add_card_group('prefix_suffix', 'placeholder', 'status_dot',
                            div_css_class='col-12')
        self.add_card_group('progress_bar', 'image', 'timestamp',
                            div_css_class='col-12')
        self.add_card_group('help_text', 'boolean_icon', 'popover',
                            div_css_class='col-12')
        self.add_card_group('separator', 'number_format', 'rating',
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

    def add_help_text_card(self):
        card = self.add_card('help_text', title='Help Text Examples',
                             header_icon='fas fa-info-circle')
        card.add_entry(value='admin@example.com', label='Email',
                       help_text='Primary contact email for notifications')
        card.add_entry(value='US-East-1', label='Region',
                       help_text='AWS region where the instance is deployed')
        card.add_entry(value='Pro Plan', label='Subscription',
                       help_text='Upgrade to Enterprise for additional features')
        card.add_entry(value='3', label='Retry count',
                       help_text='Number of times the job will retry on failure')

    def add_boolean_icon_card(self):
        card = self.add_card('boolean_icon', title='Boolean Icon Examples',
                             header_icon='fas fa-toggle-on')
        card.add_entry(value=True, label='Active', boolean_icon=True)
        card.add_entry(value=False, label='Verified', boolean_icon=True)
        card.add_entry(value=True, label='Email confirmed', boolean_icon=True)
        card.add_entry(value=False, label='Two-factor enabled', boolean_icon=True)

    def add_popover_card(self):
        card = self.add_card('popover', title='Popover Examples',
                             header_icon='fas fa-comment-dots')
        card.add_entry(value='Click me', label='Simple popover',
                       popover='This is a simple popover with just content')
        card.add_entry(value='Click me too', label='Rich popover',
                       popover={'title': 'Details', 'content': 'This popover has a title and content'})
        card.add_entry(value='Hover instead', label='Tooltip comparison',
                       tooltip='This uses a tooltip, not a popover')

    def add_separator_card(self):
        card = self.add_card('separator', title='Separator Examples',
                             header_icon='fas fa-grip-lines')
        card.add_entry(value='Section A - Item 1', label='Item')
        card.add_entry(value='Section A - Item 2', label='Item')
        card.add_entry(value='Section B - Item 1', label='Item', separator=True)
        card.add_entry(value='Section B - Item 2', label='Item')
        card.add_entry(value='Section C - Item 1', label='Item', separator=True)

    def add_number_format_card(self):
        card = self.add_card('number_format', title='Number Format Examples',
                             header_icon='fas fa-hashtag')
        card.add_entry(value=1234567, label='Population', number_format=True)
        card.add_entry(value=1234567.891, label='Revenue', number_format=2, prefix='$')
        card.add_entry(value=0.5, label='Rate', number_format=4)
        card.add_entry(value=42, label='Simple number', number_format=True)

    def add_rating_card(self):
        card = self.add_card('rating', title='Rating Examples',
                             header_icon='fas fa-star')
        card.add_entry(value=4, label='Customer rating', rating=True)
        card.add_entry(value=2, label='Quality', rating=True)
        card.add_entry(value=5, label='Perfect score', rating=True)
        card.add_entry(value=3, label='Out of 10', rating=10)


class NewFeaturesTableIndex(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_table_tooltip_card()
        self.add_table_value_link_card()
        self.add_table_badge_icon_card()
        self.add_table_copy_truncate_card()
        self.add_table_new_features_card()
        self.add_table_new_features_2_card()

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
        self.add_card_group('table_new_features_2',
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

    def add_table_new_features_2_card(self):
        card = self.add_card('table_new_features_2',
                             title='Table New Features 2',
                             template_name='table',
                             header_icon='fas fa-star',
                             extra_card_context={'table_css_class': 'table table-bordered'})
        card.add_entry(value='admin@example.com', label='Email',
                       help_text='Primary contact email')
        card.add_entry(value=True, label='Active', boolean_icon=True)
        card.add_entry(value=False, label='Verified', boolean_icon=True)
        card.add_entry(value='Click me', label='Popover',
                       popover='Details shown on click')
        card.add_entry(value='Group B', label='Section', separator=True)
        card.add_entry(value=1234567, label='Population', number_format=True)
        card.add_entry(value=1234.5, label='Revenue', number_format=2, prefix='$')
        card.add_entry(value=4, label='Rating', rating=True)
        card.add_entry(value=3, label='Quality', rating=10)


class NewFeatures2Index(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_auto_link_card()
        self.add_show_if_card()
        self.add_sparkline_card()
        self.add_old_value_card()
        self.add_searchable_card()
        self.add_exportable_card()

        self.add_card_group('auto_link', 'show_if',
                            div_css_class='col-6 float-left',
                            group_title='Auto Link & Show If')
        self.add_card_group('sparkline', 'old_value',
                            div_css_class='col-6 float-right',
                            group_title='Sparkline & Old Value')
        self.add_card_group('searchable', 'exportable',
                            div_css_class='col-12',
                            div_css='clear:both')

    def add_auto_link_card(self):
        card = self.add_card('auto_link', title='Auto Link Examples',
                             header_icon='fas fa-link')
        card.add_entry(value='Visit https://example.com for details',
                       label='URL in text',
                       auto_link=True)
        card.add_entry(value='Contact support@example.com for help',
                       label='Email in text',
                       auto_link=True)
        card.add_entry(value='See https://docs.example.com and email info@example.com',
                       label='Mixed',
                       auto_link=True)
        card.add_entry(value='No links here, just plain text',
                       label='Plain text',
                       auto_link=True)

    def add_show_if_card(self):
        company = Company.objects.first()
        if company is None:
            card = self.add_card('show_if', title='Show If Examples',
                                 header_icon='fas fa-eye')
            card.add_entry(value='Always visible', label='Static')
            card.add_entry(value='No company object to test with', label='Note')
        else:
            card = self.add_card('show_if', title='Show If Examples',
                                 details_object=company,
                                 header_icon='fas fa-eye')
            card.add_entry(value='Always visible', label='Static')
            card.add_entry(field='name', label='Name (always shown)')
            card.add_entry(field='name', label='Active only',
                           show_if=lambda obj: obj.active)
            card.add_entry(field='name', label='Inactive only',
                           show_if=lambda obj: not obj.active)

    def add_sparkline_card(self):
        card = self.add_card('sparkline', title='Sparkline Examples',
                             header_icon='fas fa-chart-line')
        card.add_entry(value=[10, 25, 15, 30, 20, 35, 28],
                       label='Weekly trend',
                       sparkline=True)
        card.add_entry(value=[5, 10, 3, 8, 12, 6, 9],
                       label='Bar chart',
                       sparkline='bar')
        card.add_entry(value=[100, 98, 95, 97, 99, 96],
                       label='Stability',
                       sparkline=True)
        card.add_entry(value=[1, 1, 1, 1],
                       label='Flat line',
                       sparkline=True)

    def add_old_value_card(self):
        card = self.add_card('old_value', title='Old Value / Diff Examples',
                             header_icon='fas fa-exchange-alt')
        card.add_entry(value='Active', label='Status',
                       old_value='Pending')
        card.add_entry(value=1500, label='Revenue',
                       old_value=1200,
                       number_format=True, prefix='$')
        card.add_entry(value=99.5, label='Accuracy',
                       old_value=97.2,
                       number_format=2, suffix='%')
        card.add_entry(value='Production', label='Environment',
                       old_value='Staging')

    def add_searchable_card(self):
        card = self.add_card('searchable', title='Searchable Card',
                             header_icon='fas fa-search',
                             searchable=True)
        items = [
            ('Alice Johnson', 'Engineering'),
            ('Bob Smith', 'Marketing'),
            ('Carol Williams', 'Engineering'),
            ('David Brown', 'Sales'),
            ('Eve Davis', 'Marketing'),
            ('Frank Miller', 'Engineering'),
            ('Grace Wilson', 'Sales'),
            ('Henry Moore', 'Support'),
        ]
        for name, dept in items:
            card.add_entry(value=dept, label=name)

    def add_exportable_card(self):
        card = self.add_card('exportable', title='Exportable Card',
                             header_icon='fas fa-file-export',
                             exportable=True)
        card.add_entry(value='Acme Corp', label='Company')
        card.add_entry(value=1500000, label='Revenue', number_format=True, prefix='$')
        card.add_entry(value=250, label='Employees', number_format=True)
        card.add_entry(value='Enterprise', label='Plan')
        card.add_entry(value='Active', label='Status', badge='bg-success')


class ImageGalleryIndex(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_image_only_gallery()
        self.add_mixed_links_gallery()
        self.add_empty_gallery()

        self.add_card_group('image_only', div_css_class='col-6 float-left')
        self.add_card_group('mixed_links', div_css_class='col-6 float-right')
        self.add_card_group('empty_gallery', div_css_class='col-12', div_css='clear:both')

    def add_image_only_gallery(self):
        images = [
            {'url': 'https://placehold.co/600x400/007bff/ffffff?text=Front', 'name': 'Front View'},
            {'url': 'https://placehold.co/600x400/28a745/ffffff?text=Side', 'name': 'Side View'},
            {'url': 'https://placehold.co/600x400/dc3545/ffffff?text=Back', 'name': 'Back View'},
        ]
        self.add_image_gallery_card(images, card_name='image_only', title='Images (backwards-compatible)')

    def add_mixed_links_gallery(self):
        image_url = 'https://placehold.co/600x400'

        #language=JS
        message_script = 'alert("Editing")'

        links = [
            {'url': f'{image_url}/007bff/ffffff?text=Product', 'name': 'Product Photo', 'type': 'image'},
            {'url': f'{image_url}/28a745/ffffff?text=Side', 'name': 'Side View', 'type': 'image'},
            {'url': 'https://example.com/datasheet.pdf', 'name': 'Data Sheet', 'type': 'data_sheet'},
            {'url': 'https://example.com/product', 'name': 'Product Page', 'type': 'product_page'},
            {'url': 'https://example.com/other', 'name': 'Other Resource', 'type': 'other'},
            {'url': 'https://example.com/other', 'name': 'With Edit', 'type': 'other', 'edit_url': f'javascript:{message_script}'},
        ]
        self.add_link_gallery_card(links, card_name='mixed_links', title='All Link Types')

    def add_empty_gallery(self):
        # Returns None — card won't render
        self.add_link_gallery_card([], card_name='empty_gallery', title='Empty Gallery')

        # Show a message card instead to demonstrate the empty behaviour
        self.add_message_card(
            card_name='empty_gallery',
            title='Empty Gallery',
            message='add_link_gallery_card() returns None when links is empty, so no card is rendered.',
        )


class ColumnSearchExample(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_people_card()
        self.add_card_group('people_col_search', div_css_class='col-12')

    def add_people_card(self):
        card = self.add_card('people_col_search',
                             title='Per-Column Search (Standard Card)',
                             template_name='table',
                             extra_card_context={'table_css_class': 'table table-bordered'},
                             column_search=True)
        people = [
            ('Alice Johnson', 'Engineering'),
            ('Bob Smith', 'Marketing'),
            ('Carol Williams', 'Engineering'),
            ('David Brown', 'Sales'),
            ('Eve Davis', 'Marketing'),
            ('Frank Miller', 'Engineering'),
            ('Grace Wilson', 'Sales'),
            ('Henry Moore', 'Support'),
            ('Isla Thompson', 'Engineering'),
            ('Jack White', 'Marketing'),
        ]
        for name, dept in people:
            card.add_entry(value=dept, label=name)


class TooltipTestIndex(MainMenu, CardMixin, TemplateView):
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_tooltip_card()
        self.add_value_link_card()

        self.add_card_group('tooltip', 'value_link',
                            div_css_class='col-6 float-left')

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


class CardBordersIndex(MainMenu, CardMixin, TemplateView):
    """Thin 1px card borders and a borderless icon card, matching a PO-style layout."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_action_buttons_card()
        self.add_po_details_card()
        self.add_icon_card()
        self.add_delivery_card()
        self.add_default_card()
        self.add_thin_standard_card()

        self.add_card_group('po_actions',
                            div_css_class='col-2 float-left')
        self.add_card_group('po_details',
                            div_css_class='col-4 float-left')
        self.add_card_group('icon_actions',
                            div_css_class='col-2 float-left')
        self.add_card_group('delivery',
                            div_css_class='col-4 float-left')
        self.add_card_group('default_border', 'thin_standard',
                            div_css_class='col-12',
                            div_css='clear:both',
                            group_title='Default vs thin (standard template)')

    def add_action_buttons_card(self):
        html = (
            '<div class="d-flex flex-column" style="gap:0.4rem">'
            '<button type="button" class="btn btn-success btn-sm">'
            '<i class="fas fa-file-invoice"></i> Process Invoice</button>'
            '<button type="button" class="btn btn-outline-info btn-sm">'
            '<i class="fas fa-truck"></i> Receive Order</button>'
            '<button type="button" class="btn btn-outline-secondary btn-sm">'
            '<i class="fas fa-calculator"></i> Calculate Fully Received</button>'
            '</div>'
        )
        self.add_html_data_card(html, card_name='po_actions', show_header=False, border='none')

    def add_po_details_card(self):
        menu = [
            MenuItem('cards_examples:hello_modal', menu_display='',
                     font_awesome='fas fa-print',
                     css_classes='django-card__header-icon',
                     attributes={'title': 'Print', 'aria-label': 'Print'}),
            MenuItem('cards_examples:hello_modal', menu_display='',
                     font_awesome='fas fa-edit',
                     css_classes='django-card__header-icon',
                     attributes={'title': 'Edit', 'aria-label': 'Edit'}),
        ]
        card = self.add_card('po_details',
                             title='Purchase Order Details',
                             template_name='table',
                             border='thin',
                             menu=menu,
                             extra_card_context={'table_css_class': 'table table-sm mb-0'})
        card.add_entry(value='25/03/2026', label='Order Date')
        card.add_entry(value='N/M - Net Monthly', label='Terms')
        card.add_entry(value='GBP', label='Currency')
        card.add_entry(value='IMI', label='Owner')

    def add_icon_card(self):
        html = (
            '<div class="d-flex align-items-center justify-content-center" '
            'style="gap:0.4rem; min-height:4.5rem">'
            '<button type="button" class="btn btn-sm btn-outline-secondary" title="Print">'
            '<i class="fas fa-print"></i></button>'
            '<button type="button" class="btn btn-sm btn-outline-secondary" title="Settings">'
            '<i class="fas fa-cog"></i></button>'
            '<button type="button" class="btn btn-sm btn-outline-secondary" title="Documents">'
            '<i class="fas fa-file-alt"></i></button>'
            '</div>'
        )
        self.add_html_data_card(html, card_name='icon_actions', show_header=False, border='thin')

    def add_delivery_card(self):
        menu = [
            MenuItem('cards_examples:hello_modal', menu_display='',
                     font_awesome='fas fa-map-marker-alt',
                     css_classes='django-card__header-icon',
                     attributes={'title': 'View on map', 'aria-label': 'View on map'}),
            MenuItem('cards_examples:hello_modal', menu_display='',
                     font_awesome='fas fa-copy',
                     css_classes='django-card__header-icon',
                     attributes={'title': 'Copy address', 'aria-label': 'Copy address'}),
        ]
        card = self.add_card('delivery',
                             title='Delivery Address',
                             template_name='table',
                             border='thin',
                             menu=menu,
                             extra_card_context={'table_css_class': 'table table-sm mb-0'})
        card.add_entry(value='Example Supplies Ltd', label='Company')
        card.add_entry(value='12 Harbour Yard', label='Address')
        card.add_entry(value='Quay Street', label='')
        card.add_entry(value='Riverton', label='')
        card.add_entry(value='RV12 4AB', label='')

    def add_default_card(self):
        card = self.add_card('default_border', title='Default Bootstrap border')
        card.add_entry(value='This is the existing card chrome', label='Style')
        card.add_entry(value='No border= argument', label='Setting')

    def add_thin_standard_card(self):
        card = self.add_card('thin_standard', title='Thin border (standard template)',
                             border='thin')
        card.add_entry(value='Same 1px hairline, list-group layout', label='Style')
        card.add_entry(value="border='thin'", label='Setting')


class PurchaseOrderLayoutIndex(MainMenu, CardMixin, TemplateView):
    """A purchase-order page built the way the compact-card layout it came from builds one.

    Everything here is a stock card option: the 1px chrome from border='thin', values
    right-aligned with table_td_css_class, a scrolling body and a fit-content card from
    card_body_css_style / card_css_style, a highlighted line from add_entry(css_class=...),
    an edit icon in the header from menu=, a highlighted line from row_css_class,
    and blank rows dropped by
    hidden_if_blank_or_none rather than filtered out before they are added.
    """
    template_name = 'cards_examples/cards.html'

    # The compact table treatment every card on this page shares.
    COMPACT = {'table_css_class': 'table table-sm mb-1',
               'table_td_css_class': 'text-right'}

    def setup_cards(self):
        self.add_details_card()
        self.add_delivery_card()
        self.add_scrolling_card()
        self.add_fit_content_card()

        self.add_card_group('po_details', div_css_class='col-xl-4 col-lg-6 col-md-6')
        self.add_card_group('delivery', div_css_class='col-xl-4 col-lg-6 col-md-6')
        self.add_card_group('lines', div_css_class='col-xl-4 col-lg-6 col-md-6')
        self.add_card_group('totals',
                            div_css_class='col-12',
                            div_css='clear:both',
                            group_title='A card only as wide as its contents')

    def add_details_card(self):
        card = self.add_card('po_details',
                             title='Purchase Order Details',
                             template_name='table',
                             border='thin',
                             hidden_if_blank_or_none=True,
                             menu=[MenuItem('cards_examples:hello_modal', menu_display='',
                                            font_awesome='fas fa-edit',
                                            css_classes='django-card__header-icon',
                                            attributes={'title': 'Edit',
                                                         'aria-label': 'Edit'})],
                             extra_card_context=self.COMPACT)
        card.add_entry(value='25/03/2026', label='Order Date')
        card.add_entry(value='02/04/2026', label='Expected Date')
        card.add_entry(value='N/M - Net Monthly', label='Terms')
        card.add_entry(value='GBP', label='Currency')
        card.add_entry(value='IMI', label='Owner')
        # Overdue lines are called out on the row itself, not the value.
        card.add_entry(value='3 lines overdue', label='Status', row_css_class='table-warning')
        # Nothing to show, so no row at all -- the blank-row drop, not a caller-side check.
        card.add_entry(value='', label='Free Issue')
        card.add_entry(value=None, label='Customer Sales Order')

    def add_delivery_card(self):
        card = self.add_card('delivery',
                             title='Delivery Address',
                             template_name='table',
                             border='thin',
                             hidden_if_blank_or_none=True,
                             menu=[MenuItem('cards_examples:hello_modal', menu_display='',
                                            font_awesome='fas fa-map-marker-alt',
                                            css_classes='django-card__header-icon',
                                            attributes={'title': 'View on map',
                                                         'aria-label': 'View on map'})],
                             extra_card_context=self.COMPACT)
        card.add_entry(value='Example Supplies Ltd', label='Company')
        card.add_entry(value='12 Harbour Yard', label='Address')
        card.add_entry(value='Quay Street', label='')
        card.add_entry(value='Riverton', label='')
        card.add_entry(value='RV12 4AB', label='')

    def add_scrolling_card(self):
        """A long card that scrolls inside itself instead of stretching the row."""
        card = self.add_card('lines',
                             title='Order Lines',
                             template_name='table',
                             border='thin',
                             extra_card_context={**self.COMPACT,
                                                 'card_body_css_style': 'max-height:200px;overflow:auto'})
        for number in range(1, 16):
            card.add_entry(value=f'{number * 3} off', label=f'Line {number}')

    def add_fit_content_card(self):
        card = self.add_card('totals',
                             title='Totals',
                             template_name='table',
                             border='thin',
                             extra_card_context={**self.COMPACT,
                                                 'card_css_style': 'width:fit-content'})
        card.add_entry(value='£1,240.00', label='Goods')
        card.add_entry(value='£248.00', label='VAT')
        card.add_entry(value='£1,488.00', label='Total', row_css_class='table-active')


class TilesIndex(MainMenu, CardMixin, TemplateView):
    """add_tiles(): a grid of small tiles for arbitrary objects.

    The four cards are the cases the API has to cover, in the order they are worth reading:
    a tile with every field, the same tile stripped back to a heading, the two shapes the
    feature was written for, and the empty state.
    """
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_every_field_card()
        self.add_minimal_card()
        self.add_colours_card()
        self.add_sizes_card()
        self.add_empty_card()

        self.add_card_group('every_field', div_css_class='col-6 float-left')
        self.add_card_group('minimal', div_css_class='col-6 float-right')
        self.add_card_group('colours', div_css_class='col-12', div_css='clear:both')
        self.add_card_group('sizes', div_css_class='col-12')
        self.add_card_group('empty_tiles', div_css_class='col-12')

    def add_every_field_card(self):
        #language=JS
        edit_script = 'alert("Editing")'
        card = self.add_card('every_field', title='Every field')
        card.add_tiles([
            Tile(key='every_field_1',
                 heading='Brass',
                 subheading='Satin',
                 meta=['£3.00', ('none in stock', 'text-danger'), ('2 items', 'text-muted')],
                 image_url='https://placehold.co/64x64/b5a642/ffffff?text=Satin',
                 badge='Default',
                 edit_url=f'javascript:{edit_script}',
                 tooltip='Brass / Satin',
                 css_class='example-tile'),
        ])

    def add_minimal_card(self):
        # The same tile with everything optional taken off: no subheading, meta, image, badge,
        # pencil or tooltip. Each part is drawn only when it was given, so the tile shrinks to
        # its heading rather than leaving empty rows behind.
        card = self.add_card('minimal', title='Heading only')
        card.add_tiles([Tile(key='minimal_1', heading='Brass')])

    def add_colours_card(self):
        """The fitting page's colours and finishes: a heading that is markup.

        A colour's name is written on the colour itself, so the heading is a span carrying an
        inline background -- built here with format_html, which escapes the name while leaving
        the span alone. The last tile's name is `Brass <script>alert(1)</script>` to make the
        point visible in the rendered page: it arrives as text either way, through heading_html
        because format_html escaped it, and through heading because the template does.
        """
        #language=JS
        edit_script = 'alert("Editing")'
        colours = [('Brass', '#b5a642', '#000', 'Satin', '£3.00', 0, True),
                   ('Chrome', '#c0c0c0', '#000', 'Polished', '£2.40', 14, False),
                   ('Black', '#1c1c1c', '#fff', 'Matt', '£1.95', 6, False),
                   ('Brass <script>alert(1)</script>', '#b5a642', '#000', 'Antique', '£4.10', 2, False)]
        tiles = []
        for index, (name, background, text, finish, price, stock, is_default) in enumerate(colours):
            stock_line = (f'{stock} in stock', '') if stock else ('none in stock', 'text-danger')
            tiles.append(Tile(
                key=f'colour_finish_{index}',
                # The app's own colour_name_block: the name written on the paint. format_html
                # escapes the name, so only the span this line builds is markup.
                heading_html=format_html(
                    '<span style="background:{};color:{};padding:4px 6px;border-radius:3px">{}</span>',
                    background, text, name),
                subheading=finish,
                meta=[price, stock_line],
                badge='Default' if is_default else None,
                edit_url=f'javascript:{edit_script}',
                tooltip=f'{name} / {finish}'))
        card = self.add_card('colours', title='Colours & Finishes (heading_html)')
        card.add_tiles(tiles,
                       empty_message='No colours or finishes yet. Use Add above to add one.',
                       width='150px')

    def add_sizes_card(self):
        # The door blank page's sizes. A size is a two-part measurement that must not wrap, which
        # is what `width` is for: at the default 150px `838 mm x 1981 mm` breaks across two lines.
        sizes = [('838 mm × 1981 mm', '£18.50', 12, 'DB-838-1981'),
                 ('762 mm × 1981 mm', '£17.20', 0, 'DB-762-1981'),
                 ('926 mm × 2040 mm', '£24.95', 3, 'DB-926-2040')]
        tiles = [Tile(key=f'size_{code}',
                      heading=size,
                      meta=[price,
                            (f'{stock} in stock', '') if stock else ('none in stock', 'text-danger'),
                            (code, 'text-muted')])
                 for size, price, stock, code in sizes]
        card = self.add_card('sizes', title='Sizes (wider tile, plain heading)')
        card.add_tiles(tiles, empty_message='No sizes yet.', width='190px')

    def add_empty_card(self):
        card = self.add_card('empty_tiles', title='Empty')
        card.add_tiles([], empty_message='No tiles yet. Use Add above to add one.')
