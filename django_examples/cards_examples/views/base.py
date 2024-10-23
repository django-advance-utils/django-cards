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
            ('cards_examples:child_cards', 'Child Cards'),
            ('cards_examples:row_styles', 'Row Styles'),
            ('cards_examples:modal_example', 'Modal Example'),
            MenuItem(url='admin:index',
                     menu_display='Admin',
                     visible=self.request.user.is_superuser),
        )


class HelloModal(Modal):
    button_container_class = 'text-center'

    def modal_content(self):
        return 'Hello<br>Message no title default OK button'
