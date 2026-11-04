"""``CardMixin.row_refresh_many`` answers ``{row: 'refresh_many'}`` on a cards view.

django-advanced-datatables' ``refresh_rows`` command (1.0.12) posts it to ask for many rows
at once. The library's ``DatatableView`` answers it, but a cards view is not one: it builds its
tables in ``setup_datatable_cards``, so the page got a ``CardPostError``. This builds the tables
the cards way and leaves the reading to the table's own ``refresh_rows``.

A capped table (``max_records``) is covered for ``row_refresh`` too: its query was sliced, and a
sliced query cannot be narrowed to the row asked for.
"""
import json
from unittest import skipUnless

from django.test import RequestFactory, TestCase
from django_datatables.datatables import DatatableTable

from cards_examples.models import Company
from cards_examples.tests.test_row_refresh import _TableView

HAS_REFRESH_ROWS = skipUnless(hasattr(DatatableTable, 'refresh_rows'), 'needs django-advanced-datatables 1.0.12')


def _refresh_many(view_cls=_TableView, **kwargs):
    view = view_cls()
    view.request = RequestFactory().post('/')
    return json.loads(view.row_refresh_many(**kwargs).content)


@HAS_REFRESH_ROWS
class TestRowRefreshMany(TestCase):

    def setUp(self):
        self.brass = Company.objects.create(name='Brass', number='7')
        self.tin = Company.objects.create(name='Tin')

    def test_the_rows_come_back_as_one_refresh_rows_command(self):
        command, = _refresh_many(table_id='companies', row_nos=[f'i{self.brass.pk}', f'i{self.tin.pk}'])
        self.assertEqual(command, {'function': 'refresh_rows', 'table_id': 'companies', 'rows': {
            f'i{self.brass.pk}': [self.brass.pk, 'Brass'],
            f'i{self.tin.pk}': [self.tin.pk, 'Tin'],
        }})

    def test_the_cards_setup_hook_builds_the_named_table_once(self):
        command, = _refresh_many(table_id='others', row_nos=[f'i{self.brass.pk}'])
        self.assertEqual(command['rows'], {f'i{self.brass.pk}': [self.brass.pk, 'Brass', '7']})

    def test_with_no_table_id_the_first_table_is_read(self):
        command, = _refresh_many(row_nos=[f'i{self.tin.pk}'])
        self.assertEqual(command['table_id'], 'companies')

    def test_nothing_to_repaint_answers_null(self):
        cases = {
            'no row_nos': {'table_id': 'companies'},
            'a string, not a list': {'table_id': 'companies', 'row_nos': f'i{self.brass.pk}'},
            'a number': {'table_id': 'companies', 'row_nos': 12},
        }
        for name, kwargs in cases.items():
            with self.subTest(name):
                self.assertEqual(_refresh_many(**kwargs), [{'function': 'null'}])

    def test_the_pages_seq_comes_back(self):
        """Two refreshes of one table can be in flight; the page tells their replies apart by it."""
        command, = _refresh_many(table_id='companies', row_nos=[f'i{self.tin.pk}'], seq=4)
        self.assertEqual(command['seq'], 4)
        self.assertEqual(command['rows'], {f'i{self.tin.pk}': [self.tin.pk, 'Tin']})

    def test_no_seq_sent_none_added(self):
        command, = _refresh_many(table_id='companies', row_nos=[f'i{self.tin.pk}'])
        self.assertNotIn('seq', command)

    def test_an_unknown_table_answers_with_no_rows_so_a_waiting_page_hears_back(self):
        self.assertEqual(
            _refresh_many(table_id='nope', row_nos=[f'i{self.brass.pk}'], seq=2),
            [{'function': 'refresh_rows', 'table_id': 'nope', 'rows': {}, 'seq': 2}],
        )


class _Capped(_TableView):
    def setup_table_companies(self, table, details_object):
        super().setup_table_companies(table, details_object)
        table.max_records = 1


class TestACappedTable(TestCase):

    def setUp(self):
        self.brass = Company.objects.create(name='Brass')
        self.copper = Company.objects.create(name='Copper')

    def test_row_refresh_reads_a_row_past_the_cap_and_puts_the_cap_back(self):
        view = _Capped()
        view.request = RequestFactory().post('/')
        command, = json.loads(view.row_refresh(table_id='companies', row_no=f'i{self.copper.pk}').content)
        self.assertEqual(command['data'], [self.copper.pk, 'Copper'])
        self.assertEqual(view.tables['companies'].max_records, 1)

    @HAS_REFRESH_ROWS
    def test_row_refresh_many_reads_past_the_cap(self):
        view = _Capped()
        view.request = RequestFactory().post('/')
        response = view.row_refresh_many(table_id='companies', row_nos=[f'i{self.brass.pk}', f'i{self.copper.pk}'])
        command, = json.loads(response.content)
        self.assertEqual(len(command['rows']), 2)
        self.assertEqual(view.tables['companies'].max_records, 1)
