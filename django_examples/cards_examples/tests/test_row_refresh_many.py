"""``CardMixin.row_refresh_many`` repaints many datatable rows in one request.

django-advanced-datatables' ``refresh_rows`` command (1.0.12) posts ``{row: 'refresh_many'}``
with the ids of the rows to repaint when it is not handed the rows themselves. django-cards did
not answer it, so the page got a ``CardPostError``. The rows are read as ``row_refresh`` reads
one -- the table the view builds, its ``get_<table_id>_query``, its own filters -- and come back
as one ``refresh_rows`` command, keyed by row id.

A row that is not there, or an id that is not one, is left out; nothing to repaint answers
``null``. A table with ``max_records`` set is read too: its query was sliced, and a sliced query
cannot be narrowed to the rows asked for -- which held for ``row_refresh`` as well.
"""
import json

from django.db.models import Q
from django.test import RequestFactory, TestCase

from cards_examples.models import Company
from cards_examples.tests.test_row_refresh import _refresh, _TableView


def _refresh_many(view_cls=_TableView, **kwargs):
    view = view_cls()
    view.request = RequestFactory().post('/')
    return json.loads(view.row_refresh_many(**kwargs).content)


class TestRowRefreshMany(TestCase):

    def setUp(self):
        self.brass = Company.objects.create(name='Brass', number='7')
        self.copper = Company.objects.create(name='Copper')
        self.tin = Company.objects.create(name='Tin')

    def ids(self, *companies):
        return [f'i{c.pk}' for c in companies]

    def test_the_rows_come_back_as_one_refresh_rows_command(self):
        command, = _refresh_many(table_id='companies', row_nos=self.ids(self.brass, self.tin))
        self.assertEqual(command, {'function': 'refresh_rows', 'table_id': 'companies', 'rows': {
            f'i{self.brass.pk}': [self.brass.pk, 'Brass'],
            f'i{self.tin.pk}': [self.tin.pk, 'Tin'],
        }})

    def test_the_named_table_is_the_one_read_and_the_first_by_default(self):
        command, = _refresh_many(table_id='others', row_nos=self.ids(self.brass))
        self.assertEqual(command['rows'], {f'i{self.brass.pk}': [self.brass.pk, 'Brass', '7']})
        command, = _refresh_many(row_nos=self.ids(self.copper))
        self.assertEqual(command['table_id'], 'companies')
        self.assertEqual(command['rows'], {f'i{self.copper.pk}': [self.copper.pk, 'Copper']})

    def test_rows_not_there_and_ids_that_are_not_ones_are_left_out(self):
        gone = Company.objects.create(name='Gone')
        gone_pk = gone.pk
        gone.delete()
        row_nos = self.ids(self.brass) + [f'i{gone_pk}', 'i', 'x1', 'i١', 'i²', 'i' + '9' * 20,
                                          f'i{2 ** 63}', 12, None, f'i{self.brass.pk}']
        command, = _refresh_many(table_id='companies', row_nos=row_nos)
        self.assertEqual(command['rows'], {f'i{self.brass.pk}': [self.brass.pk, 'Brass']})

    def test_every_row_gone_is_an_empty_refresh(self):
        gone = Company.objects.create(name='Gone')
        gone_pk = gone.pk
        gone.delete()
        command, = _refresh_many(table_id='companies', row_nos=[f'i{gone_pk}'])
        self.assertEqual(command['rows'], {})

    def test_nothing_to_repaint_answers_null(self):
        cases = {
            'no row_nos': {'table_id': 'companies'},
            'an empty list': {'table_id': 'companies', 'row_nos': []},
            'a string, not a list': {'table_id': 'companies', 'row_nos': f'i{self.brass.pk}'},
            'no id that is one': {'table_id': 'companies', 'row_nos': ['i', 'x']},
            'an unknown table': {'table_id': 'nope', 'row_nos': self.ids(self.brass)},
        }
        for name, kwargs in cases.items():
            with self.subTest(name):
                self.assertEqual(_refresh_many(**kwargs), [{'function': 'null'}])

    def test_the_tables_filter_and_the_views_query_still_apply(self):
        class Filtered(_TableView):
            table_filter = Q(name__startswith='B') | Q(name__startswith='C')

            def get_companies_query(self, table, **kwargs):
                return table.get_query(**kwargs).exclude(name='Copper')

        command, = _refresh_many(Filtered, table_id='companies', row_nos=self.ids(self.brass, self.copper, self.tin))
        self.assertEqual(list(command['rows']), [f'i{self.brass.pk}'])

    def test_a_long_list_is_read_in_batches(self):
        class SmallBatches(_TableView):
            REFRESH_BATCH_SIZE = 2

        command, = _refresh_many(SmallBatches, table_id='companies',
                                 row_nos=self.ids(self.brass, self.copper, self.tin, self.brass))
        self.assertEqual(set(command['rows']), set(self.ids(self.brass, self.copper, self.tin)))

    def test_a_seq_comes_back_on_the_command(self):
        command, = _refresh_many(table_id='companies', row_nos=self.ids(self.brass), seq=3)
        self.assertEqual(command['seq'], 3)
        command, = _refresh_many(table_id='companies', row_nos=self.ids(self.brass))
        self.assertNotIn('seq', command)


class _Capped(_TableView):
    def setup_table_companies(self, table, details_object):
        super().setup_table_companies(table, details_object)
        table.max_records = 1


class TestATableWithMaxRecords(TestCase):

    def setUp(self):
        self.brass = Company.objects.create(name='Brass')
        self.copper = Company.objects.create(name='Copper')

    def test_rows_past_the_cap_are_read(self):
        command, = _refresh_many(_Capped, table_id='companies', row_nos=[f'i{self.brass.pk}', f'i{self.copper.pk}'])
        self.assertEqual(len(command['rows']), 2)

    def test_one_row_is_read_too(self):
        command, = _refresh(_Capped, table_id='companies', row_no=f'i{self.copper.pk}')
        self.assertEqual(command['data'], [self.copper.pk, 'Copper'])

    def test_the_cap_is_put_back(self):
        view = _Capped()
        view.request = RequestFactory().post('/')
        view.row_refresh_many(table_id='companies', row_nos=[f'i{self.brass.pk}'])
        self.assertEqual(view.tables['companies'].max_records, 1)
