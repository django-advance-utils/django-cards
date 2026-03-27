from ajax_helpers.mixins import AjaxHelpers
from django_menus.menu import MenuMixin, MenuItem
from django_modals.modals import Modal


class MainMenu(AjaxHelpers, MenuMixin):
    def setup_menu(self):
        # noinspection PyUnresolvedReferences
        self.add_menu('main_menu').add_items(
            ('cards_examples:index', 'Home'),
            ('cards_examples:groups', 'Groups'),
            MenuItem(menu_display='Lists', dropdown=(
                ('cards_examples:list,-', 'List'),
                ('cards_examples:list_empty,-', 'List Empty'),
                ('cards_examples:list_adv,-', 'List Advanced'),
                ('cards_examples:tree,-', 'Tree'),
            )),
            MenuItem(menu_display='Datatables', dropdown=(
                ('cards_examples:datatable', 'Datatable'),
                ('cards_examples:datatable_order', 'Datatable Order'),
                ('cards_examples:linked_datatables', 'Linked - Company Drilldown'),
                ('cards_examples:linked_datatables_payments', 'Linked - Payment Drilldown'),
                ('cards_examples:linked_datatables_four', 'Linked - Four Level'),
            )),
            MenuItem(menu_display='Treegrid', dropdown=(
                ('cards_examples:treegrid', 'Basic'),
                ('cards_examples:treegrid_editable', 'Editable'),
                ('cards_examples:treegrid_multi', 'Multi Level'),
                ('cards_examples:treegrid_compact', 'Compact'),
                ('cards_examples:treegrid_expanded', 'Expanded'),
                ('cards_examples:treegrid_payments', 'Payments'),
                ('cards_examples:treegrid_widgets', 'Widgets (Auto Save)'),
                ('cards_examples:treegrid_batch', 'Widgets (Batch Save)'),
                ('cards_examples:treegrid_select', 'Row Selection'),
                ('cards_examples:treegrid_advanced', 'Advanced'),
                ('cards_examples:treegrid_self', 'Self-Dispatch'),
                ('cards_examples:treegrid_static', 'Static Data'),
                ('cards_examples:treegrid_dual', 'Dual Grid'),
                ('cards_examples:treegrid_calculator', 'Calculator'),
                ('cards_examples:treegrid_styled', 'Styled Cells'),
                ('cards_examples:treegrid_full', 'Full Featured'),
                ('cards_examples:treegrid_colspan', 'Colspan Headers'),
            )),
            MenuItem(menu_display='Accordion', dropdown=(
                ('cards_examples:accordion', 'Basic'),
                ('cards_examples:accordion_ajax', 'AJAX Loading'),
                ('cards_examples:accordion_multi', 'Multi Open'),
                ('cards_examples:accordion_layout', 'Layout'),
            )),
            MenuItem(menu_display='Panel Layout', dropdown=(
                ('cards_examples:panel_sidebar', 'Sidebar'),
                ('cards_examples:panel_three_col', 'Three Column'),
                ('cards_examples:panel_nested', 'Nested'),
                ('cards_examples:panel_holy_grail', 'Holy Grail'),
                ('cards_examples:panel_datatable', 'With Datatable'),
                ('cards_examples:panel_fullscreen', 'Fullscreen'),
                ('cards_examples:panel_accordion', 'Accordion'),
                ('cards_examples:panel_iframe', 'Iframe'),
                ('cards_examples:panel_linked_dt', 'Linked Datatables'),
                ('cards_examples:panel_detail_dt', 'Detail Datatables'),
                ('cards_examples:panel_tabs', 'Tabs'),
            )),
            MenuItem(menu_display='Display', dropdown=(
                ('cards_examples:child_cards', 'Child Cards'),
                ('cards_examples:row_styles', 'Row Styles'),
                ('cards_examples:new_features', 'New Features'),
                ('cards_examples:new_features_table', 'New Features (Table)'),
                ('cards_examples:new_features_2', 'New Features 2'),
                ('cards_examples:image_gallery', 'Image Gallery'),
            )),
            MenuItem(url='admin:index',
                     menu_display='Admin',
                     visible=self.request.user.is_superuser),
        )


class HelloModal(Modal):
    button_container_class = 'text-center'

    def modal_content(self):
        return 'Hello<br>Message no title default OK button'
