from ajax_helpers.mixins import AjaxHelpers
from django_menus.menu import MenuMixin, MenuItem
from django_modals.modals import Modal


class MainMenu(AjaxHelpers, MenuMixin):
    def setup_menu(self):
        # noinspection PyUnresolvedReferences
        self.add_menu('main_menu').add_items(
            ('cards_examples:index', 'Home'),
            ('cards_examples:groups', 'Groups'),
            ('cards_examples:list,-', 'List'),
            ('cards_examples:list_empty,-', 'List Empty'),
            ('cards_examples:list_adv,-', 'List Adv'),
            ('cards_examples:tree,-', 'Tree'),
            ('cards_examples:datatable', 'Datatable'),
            ('cards_examples:datatable_order', 'Datatable Order'),
            MenuItem(menu_display='Linked DT', dropdown=(
                ('cards_examples:linked_datatables', 'Company Drilldown'),
                ('cards_examples:linked_datatables_payments', 'Payment Drilldown'),
                ('cards_examples:linked_datatables_four', 'Four Level'),
            )),
            ('cards_examples:child_cards', 'Child Cards'),
            ('cards_examples:row_styles', 'Row Styles'),
            ('cards_examples:new_features', 'New Features'),
            ('cards_examples:new_features_table', 'New Features (Table)'),
            ('cards_examples:new_features_2', 'New Features 2'),
            ('cards_examples:image_gallery', 'Image Gallery'),
            MenuItem(url='admin:index',
                     menu_display='Admin',
                     visible=self.request.user.is_superuser),
        )


class HelloModal(Modal):
    button_container_class = 'text-center'

    def modal_content(self):
        return 'Hello<br>Message no title default OK button'
