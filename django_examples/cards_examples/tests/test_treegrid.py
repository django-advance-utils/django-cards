import json
import re
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model

from cards.includes import FancytreeJS, FancytreeAwesomeSkinCSS
from cards_examples.models import Company, CompanyCategory
from cards_examples.views.treegrid import (
    TreegridBasicExample, TreegridEditableExample, TreegridMultiLevelExample,
    TreegridCompactExample, TreegridPaymentsExample, TreegridExpandedExample,
    TreegridWidgetsExample, TreegridFullExample, TreegridBatchExample, TreegridColspanExample,
    TreegridStyledExample,
    TreegridData, TreegridMultiData, TreegridCompactData, TreegridPaymentsData,
    TreegridWidgetsData, TreegridFullData, TreegridColspanData, TreegridStyledData,
)

User = get_user_model()


class TestFancytreeIncludes(TestCase):
    """Verify Fancytree CDN includes generate correct URLs."""

    def test_js_url_no_double_scheme(self):
        js = FancytreeJS('', False)
        output = js.includes(cdn=True)
        self.assertNotIn('https://https://', output)
        self.assertIn('https://cdn.jsdelivr.net/', output)

    def test_js_url_correct_path(self):
        js = FancytreeJS('', False)
        output = js.includes(cdn=True)
        self.assertIn('dist/jquery.fancytree-all-deps.min.js', output)
        self.assertNotIn('dist/js/', output)

    def test_css_url_no_double_scheme(self):
        css = FancytreeAwesomeSkinCSS('', False)
        output = css.includes(cdn=True)
        self.assertNotIn('https://https://', output)
        self.assertIn('https://cdn.jsdelivr.net/', output)

    def test_css_url_correct_path(self):
        css = FancytreeAwesomeSkinCSS('', False)
        output = css.includes(cdn=True)
        self.assertIn('dist/skin-awesome/ui.fancytree.min.css', output)
        self.assertNotIn('dist/css/', output)


class TreegridViewTestMixin:
    """Shared helpers for treegrid view tests."""

    view_class = None

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User(username='test', is_superuser=False)

    def _render(self):
        request = self.factory.get('/treegrid/')
        request.user = self.user
        response = self.view_class.as_view()(request)
        response.render()
        return response.content.decode()

    def _count_filter_inputs(self, html):
        return len(re.findall(r'<input[^>]*filter_input', html))


class TestTreegridBasic(TreegridViewTestMixin, TestCase):
    view_class = TreegridBasicExample

    def test_renders_200(self):
        request = self.factory.get('/treegrid/')
        request.user = self.user
        response = self.view_class.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_fancytree_included(self):
        html = self._render()
        self.assertIn('jquery.fancytree-all-deps.min.js', html)
        self.assertIn('ui.fancytree.min.css', html)

    def test_no_double_https(self):
        html = self._render()
        self.assertNotIn('https://https://', html)

    def test_datatable_matching_classes(self):
        html = self._render()
        self.assertIn('card django-card', html)
        self.assertIn('card-body cards-list', html)
        self.assertIn('display compact smalltext table-sm table w-100', html)

    def test_filter_hidden(self):
        html = self._render()
        self.assertEqual(self._count_filter_inputs(html), 0)

    def test_no_duplicate_fancytree_js(self):
        html = self._render()
        count = html.count('jquery.fancytree-all-deps.min.js')
        self.assertEqual(count, 1)

    def test_outline_plus_minus_icons_in_css(self):
        html = self._render()
        # f0fe = fa-plus-square, f146 = fa-minus-square
        self.assertIn('\\f0fe', html)
        self.assertIn('\\f146', html)
        # Outline style: font-weight 400 (regular), not 900 (solid)
        self.assertIn('font-weight: 400', html)
        # Old caret icons should not be present
        self.assertNotIn('\\f0da', html)
        self.assertNotIn('\\f0d7', html)

    def test_fancytree_init_script(self):
        html = self._render()
        self.assertIn('.fancytree(', html)

    def test_expand_all_disabled(self):
        html = self._render()
        self.assertIn('EXPAND_ALL = false', html)

    def test_data_url(self):
        html = self._render()
        self.assertIn('/treegrid/data/', html)


class TestTreegridEditable(TreegridViewTestMixin, TestCase):
    view_class = TreegridEditableExample

    def test_renders_200(self):
        request = self.factory.get('/treegrid/editable/')
        request.user = self.user
        response = self.view_class.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_filter_shown(self):
        html = self._render()
        self.assertEqual(self._count_filter_inputs(html), 1)

    def test_editable_columns(self):
        html = self._render()
        self.assertIn('READ_ONLY = false', html)

    def test_footer_present(self):
        html = self._render()
        self.assertIn('Double-click', html)

    def test_expand_collapse_buttons(self):
        html = self._render()
        self.assertIn('_expand_all', html)
        self.assertIn('_collapse_all', html)


class TestTreegridMultiLevel(TreegridViewTestMixin, TestCase):
    view_class = TreegridMultiLevelExample

    def test_renders_200(self):
        request = self.factory.get('/treegrid/multi-level/')
        request.user = self.user
        response = self.view_class.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_filter_shown(self):
        html = self._render()
        self.assertEqual(self._count_filter_inputs(html), 1)

    def test_height_700(self):
        html = self._render()
        self.assertIn('700px', html)

    def test_data_url(self):
        html = self._render()
        self.assertIn("DATA_MODE = 'ajax'", html)


class TestTreegridCompact(TreegridViewTestMixin, TestCase):
    view_class = TreegridCompactExample

    def test_renders_200(self):
        request = self.factory.get('/treegrid/compact/')
        request.user = self.user
        response = self.view_class.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_filter_hidden(self):
        html = self._render()
        self.assertEqual(self._count_filter_inputs(html), 0)

    def test_height_400(self):
        html = self._render()
        self.assertIn('400px', html)


class TestTreegridExpanded(TreegridViewTestMixin, TestCase):
    view_class = TreegridExpandedExample

    def test_renders_200(self):
        request = self.factory.get('/treegrid/expanded/')
        request.user = self.user
        response = self.view_class.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_expand_all_enabled(self):
        html = self._render()
        self.assertIn('EXPAND_ALL = true', html)

    def test_filter_shown_by_default(self):
        html = self._render()
        self.assertEqual(self._count_filter_inputs(html), 1)


class TestTreegridWidgets(TreegridViewTestMixin, TestCase):
    view_class = TreegridWidgetsExample

    def test_renders_200(self):
        request = self.factory.get('/treegrid/widgets/')
        request.user = self.user
        response = self.view_class.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_not_read_only(self):
        html = self._render()
        self.assertIn('READ_ONLY = false', html)

    def test_tree_column_not_editable(self):
        """Tree column (Name) should not be marked editable."""
        html = self._render()
        # Column 0 should not appear in EDITABLE_FIELDS
        # The columns JSON should show first column without editable
        self.assertIn('"field": "title"', html)
        # Name column has no 'editable': true
        import json
        # Extract COLUMNS JSON from script
        start = html.index('var COLUMNS = ') + len('var COLUMNS = ')
        end = html.index(';\n', start)
        columns = json.loads(html[start:end])
        self.assertFalse(columns[0].get('editable', False))

    def test_checkbox_column_defined(self):
        html = self._render()
        self.assertIn('"type": "checkbox"', html)

    def test_select_column_defined(self):
        html = self._render()
        self.assertIn('"type": "select"', html)

    def test_select_options_present(self):
        html = self._render()
        self.assertIn('"label": "Mr"', html)
        self.assertIn('"label": "Mrs"', html)

    def test_data_url(self):
        html = self._render()
        self.assertIn("DATA_MODE = 'ajax'", html)

    def test_footer_present(self):
        html = self._render()
        self.assertIn('Title', html)
        self.assertIn('Importance', html)


class TestTreegridWidgetsData(TestCase):

    def test_root_nodes(self):
        request = RequestFactory().get('/')
        response = TreegridWidgetsData.as_view()(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIsInstance(data, list)

    def test_invalid_parent(self):
        request = RequestFactory().get('/', {'parent': 'company_999999'})
        response = TreegridWidgetsData.as_view()(request)
        self.assertEqual(json.loads(response.content), [])

    def test_person_data_has_widget_fields(self):
        """Check that person nodes include is_active and person_title fields."""
        request = RequestFactory().get('/')
        response = TreegridWidgetsData.as_view()(request)
        data = json.loads(response.content)
        if data:
            # Get children of first company
            first_key = data[0]['key']
            request2 = RequestFactory().get('/', {'parent': first_key})
            response2 = TreegridWidgetsData.as_view()(request2)
            children = json.loads(response2.content)
            if children:
                person = children[0]
                self.assertIn('is_active', person['data'])
                self.assertIn('person_title', person['data'])
                self.assertIn('first_name', person['data'])


class TestTreegridBatch(TreegridViewTestMixin, TestCase):
    view_class = TreegridBatchExample

    def test_renders_200(self):
        request = self.factory.get('/treegrid/batch/')
        request.user = self.user
        response = self.view_class.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_batch_save_mode(self):
        html = self._render()
        self.assertIn("SAVE_MODE = 'batch'", html)

    def test_save_button_present(self):
        html = self._render()
        self.assertIn('_save_btn', html)
        self.assertIn('fa-save', html)

    def test_discard_button_present(self):
        html = self._render()
        self.assertIn('_discard_btn', html)
        self.assertIn('Discard', html)

    def test_changes_counter_present(self):
        html = self._render()
        self.assertIn('_changes', html)

    def test_batch_save_js(self):
        html = self._render()
        self.assertIn('_batch_save', html)
        self.assertIn('pendingChanges', html)

    def test_auto_save_not_used(self):
        """In batch mode, individual changes should not post immediately."""
        html = self._render()
        # recordChange should check SAVE_MODE, not post directly
        self.assertIn("if (SAVE_MODE === 'batch')", html)


class TestTreegridReload(TreegridViewTestMixin, TestCase):
    """Test the reload_treegrid command and on_change support."""
    view_class = TreegridBasicExample

    def test_reload_function_registered(self):
        html = self._render()
        self.assertIn('window._treegridRegistry', html)
        self.assertIn('reloadTreegrid', html)

    def test_reload_command_registered(self):
        html = self._render()
        self.assertIn('reload_treegrid', html)
        self.assertIn('ajax_helpers.command_functions', html)

    def test_on_change_reload_support(self):
        html = self._render()
        self.assertIn('on_change', html)
        self.assertIn("=== 'reload'", html)

    def test_treegrid_reload_response_method(self):
        """The CardMixin should have a treegrid_reload_response helper."""
        from cards.standard import CardMixin
        self.assertTrue(hasattr(CardMixin, 'treegrid_reload_response'))


class TestTreegridCellCommands(TestCase):
    """Test the cell update/style ajax_helpers commands and Python helpers."""

    def test_update_cell_command_registered(self):
        """JS should register treegrid_update_cell command."""
        factory = RequestFactory()
        request = factory.get('/treegrid/')
        request.user = User(username='test', is_superuser=False)
        response = TreegridBasicExample.as_view()(request)
        response.render()
        html = response.content.decode()
        self.assertIn('treegrid_update_cell', html)
        self.assertIn('treegrid_style_cell', html)
        self.assertIn('treegrid_style_row', html)

    def test_update_cell_helper(self):
        from cards.standard import CardMixin
        self.assertTrue(hasattr(CardMixin, 'treegrid_update_cell'))

    def test_style_cell_helper(self):
        from cards.standard import CardMixin
        self.assertTrue(hasattr(CardMixin, 'treegrid_style_cell'))

    def test_style_row_helper(self):
        from cards.standard import CardMixin
        self.assertTrue(hasattr(CardMixin, 'treegrid_style_row'))


class TestTreegridWidgetsAutoSave(TreegridViewTestMixin, TestCase):
    """Verify the Widgets example uses auto save mode."""
    view_class = TreegridWidgetsExample

    def test_auto_save_mode(self):
        html = self._render()
        self.assertIn("SAVE_MODE = 'auto'", html)

    def test_no_save_button(self):
        html = self._render()
        self.assertNotIn('fa-save', html)


class TestTreegridFull(TreegridViewTestMixin, TestCase):
    view_class = TreegridFullExample

    def test_renders_200(self):
        request = self.factory.get('/treegrid/full/')
        request.user = self.user
        response = self.view_class.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_column_filter_row_present(self):
        html = self._render()
        self.assertIn('treegrid-column-filters', html)
        self.assertIn('treegrid-col-filter', html)

    def test_select_filter_for_category(self):
        html = self._render()
        self.assertIn('Technology', html)
        self.assertIn('Finance', html)

    def test_toolbar_buttons(self):
        html = self._render()
        self.assertIn('treegrid-toolbar-btn', html)
        self.assertIn('New Group', html)
        self.assertIn('New Company', html)
        self.assertIn('fa-folder-plus', html)

    def test_action_column(self):
        html = self._render()
        self.assertIn('"type": "actions"', html)
        self.assertIn('fa-pencil-alt', html)
        self.assertIn('fa-info-circle', html)

    def test_boolean_column(self):
        html = self._render()
        self.assertIn('"type": "boolean"', html)

    def test_column_filter_js(self):
        html = self._render()
        self.assertIn('SHOW_COL_FILTERS = true', html)

    def test_global_filter_hidden(self):
        """Full example uses column filters instead of global filter."""
        html = self._render()
        self.assertEqual(self._count_filter_inputs(html), 0)

    def test_icon_classes(self):
        html = self._render()
        self.assertIn('text-warning', html)
        self.assertIn('far fa-building', html)

    def test_data_url(self):
        html = self._render()
        self.assertIn("DATA_MODE = 'ajax'", html)


class TestTreegridFullData(TestCase):

    def test_root_nodes(self):
        request = RequestFactory().get('/')
        response = TreegridFullData.as_view()(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIsInstance(data, list)
        if data:
            self.assertIn('created', data[0]['data'])
            self.assertIn('modified', data[0]['data'])

    def test_invalid_parent(self):
        request = RequestFactory().get('/', {'parent': 'bogus_123'})
        response = TreegridFullData.as_view()(request)
        self.assertEqual(json.loads(response.content), [])


class TestTreegridColspan(TreegridViewTestMixin, TestCase):
    view_class = TreegridColspanExample

    def test_renders_200(self):
        request = self.factory.get('/treegrid/colspan/')
        request.user = self.user
        response = self.view_class.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_colspan_header_present(self):
        html = self._render()
        self.assertIn('colspan="3"', html)
        self.assertIn('Selections', html)

    def test_rowspan_header_present(self):
        html = self._render()
        self.assertIn('rowspan="2"', html)

    def test_option_values_colspan(self):
        html = self._render()
        self.assertIn('colspan="2"', html)
        self.assertIn('Option Values', html)

    def test_visible_for_in_columns(self):
        html = self._render()
        self.assertIn('"visible_for"', html)
        self.assertIn('"item"', html)
        self.assertIn('"group"', html)

    def test_header_css_class(self):
        html = self._render()
        self.assertIn('text-center', html)

    def test_hidden_header_row(self):
        """Fancytree needs a hidden row with one th per column for column counting."""
        html = self._render()
        self.assertIn('treegrid-hidden-header', html)

    def test_hidden_row_has_all_columns(self):
        """Hidden header row must have 8 th cells (one per data column)."""
        import re
        html = self._render()
        hidden_row = re.search(
            r'<tr class="treegrid-hidden-header">(.*?)</tr>', html, re.DOTALL)
        self.assertIsNotNone(hidden_row, 'Hidden header row not found')
        th_count = hidden_row.group(1).count('<th>')
        self.assertEqual(th_count, 8, f'Expected 8 th cells, got {th_count}')

    def test_node_column_set_to_4(self):
        """Tree node should render in column 4 (Subitem Type / Style Name)."""
        html = self._render()
        self.assertIn('NODE_COLUMN = 4', html)

    def test_node_column_in_fancytree_config(self):
        html = self._render()
        self.assertIn('nodeColumnIdx: NODE_COLUMN', html)

    def test_data_url(self):
        html = self._render()
        self.assertIn("DATA_MODE = 'ajax'", html)

    def test_rendercells_skips_node_column(self):
        """renderCells should skip NODE_COLUMN, not hardcoded 0."""
        html = self._render()
        self.assertIn('if (i === NODE_COLUMN) continue;', html)


class TestTreegridColspanData(TestCase):

    def test_root_nodes(self):
        request = RequestFactory().get('/')
        response = TreegridColspanData.as_view()(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIsInstance(data, list)
        if data:
            self.assertEqual(data[0]['data']['type'], 'category')

    def test_invalid_parent(self):
        request = RequestFactory().get('/', {'parent': 'bogus_123'})
        response = TreegridColspanData.as_view()(request)
        self.assertEqual(json.loads(response.content), [])


class TestTreegridStyled(TreegridViewTestMixin, TestCase):
    view_class = TreegridStyledExample

    def test_renders_200(self):
        request = self.factory.get('/treegrid/styled/')
        request.user = self.user
        response = self.view_class.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_data_url(self):
        html = self._render()
        self.assertIn("DATA_MODE = 'ajax'", html)


class TestTreegridStyledData(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.cat = CompanyCategory.objects.create(name='TestCat')
        cls.company = Company.objects.create(name='TestCo', company_category=cls.cat, importance=2)

    def test_root_nodes_have_row_bg(self):
        request = RequestFactory().get('/')
        response = TreegridStyledData.as_view()(request)
        data = json.loads(response.content)
        self.assertGreater(len(data), 0)
        self.assertIn('_row_bg', data[0]['data'])

    def test_root_nodes_have_cell_colours(self):
        request = RequestFactory().get('/')
        response = TreegridStyledData.as_view()(request)
        data = json.loads(response.content)
        self.assertIn('width_val__color', data[0]['data'])
        self.assertIn('thickness__color', data[0]['data'])

    def test_children_have_cell_bg(self):
        request = RequestFactory().get('/', {'parent': f'category_{self.cat.id}'})
        response = TreegridStyledData.as_view()(request)
        children = json.loads(response.content)
        self.assertGreater(len(children), 0)
        d = children[0]['data']
        self.assertIn('thickness__bg', d)
        self.assertIn('width_val__bg', d)
        self.assertIn('material__bg', d)


class TestTreegridPayments(TreegridViewTestMixin, TestCase):
    view_class = TreegridPaymentsExample

    def test_renders_200(self):
        request = self.factory.get('/treegrid/payments/')
        request.user = self.user
        response = self.view_class.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_filter_shown(self):
        html = self._render()
        self.assertEqual(self._count_filter_inputs(html), 1)

    def test_data_url(self):
        html = self._render()
        self.assertIn("DATA_MODE = 'ajax'", html)


# ---------------------------------------------------------------------------
# Data endpoint tests
# ---------------------------------------------------------------------------

class TestTreegridData(TestCase):

    def test_root_nodes_json_array(self):
        request = RequestFactory().get('/')
        response = TreegridData.as_view()(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIsInstance(data, list)

    def test_root_nodes_have_required_fields(self):
        request = RequestFactory().get('/')
        response = TreegridData.as_view()(request)
        data = json.loads(response.content)
        if data:
            node = data[0]
            for field in ('title', 'key', 'folder'):
                self.assertIn(field, node)

    def test_invalid_parent(self):
        request = RequestFactory().get('/', {'parent': 'bogus_123'})
        response = TreegridData.as_view()(request)
        self.assertEqual(json.loads(response.content), [])

    def test_nonexistent_company(self):
        request = RequestFactory().get('/', {'parent': 'company_999999'})
        response = TreegridData.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), [])


class TestTreegridMultiData(TestCase):

    def test_root_nodes(self):
        request = RequestFactory().get('/')
        response = TreegridMultiData.as_view()(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIsInstance(data, list)
        if data:
            self.assertEqual(data[0]['data']['node_type'], 'Category')

    def test_invalid_parent(self):
        request = RequestFactory().get('/', {'parent': 'bogus_123'})
        response = TreegridMultiData.as_view()(request)
        self.assertEqual(json.loads(response.content), [])


class TestTreegridCompactData(TestCase):

    def test_root_nodes_are_companies(self):
        request = RequestFactory().get('/')
        response = TreegridCompactData.as_view()(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIsInstance(data, list)
        if data:
            self.assertTrue(data[0]['key'].startswith('company_'))

    def test_invalid_parent(self):
        request = RequestFactory().get('/', {'parent': 'company_999999'})
        response = TreegridCompactData.as_view()(request)
        self.assertEqual(json.loads(response.content), [])


class TestTreegridPaymentsData(TestCase):

    def test_root_nodes_are_companies(self):
        request = RequestFactory().get('/')
        response = TreegridPaymentsData.as_view()(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIsInstance(data, list)
        if data:
            self.assertTrue(data[0]['key'].startswith('company_'))
            self.assertIn('amount', data[0]['data'])

    def test_invalid_parent(self):
        request = RequestFactory().get('/', {'parent': 'company_999999'})
        response = TreegridPaymentsData.as_view()(request)
        self.assertEqual(json.loads(response.content), [])
