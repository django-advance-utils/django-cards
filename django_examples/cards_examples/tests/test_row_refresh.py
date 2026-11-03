"""``CardMixin.row_refresh`` repaints one datatable row: the ``{row: 'refresh'}`` command.

ajax_helpers' ``refresh_row`` posts it when called without ``data``. django-cards answered
``row_edit`` but not this, so a page asking for one row to be repainted got a ``CardPostError``.
It answers with django-datatables' own ``refresh_row`` command, which the page already knows.

When there is nothing to repaint -- no row number, a table the view does not build, a row that
has gone or been filtered out since -- it answers ``null`` rather than a 500, and the row waits
for the next reload. A table whose filter is a ``Q`` is narrowed to the row too: the table's own
``refresh_row_command`` writes the id into its filter as a dict key, which a ``Q`` cannot take.
"""
import json

from ajax_helpers.mixins import AjaxHelpers
from django.db.models import Q
from django.test import RequestFactory, TestCase
from django.views.generic import TemplateView

from cards.base import CARD_TYPE_DATATABLE
from cards.standard import CardMixin
from cards_examples.models import Company


class _TableView(AjaxHelpers, CardMixin, TemplateView):
    table_filter = None

    def setup_datatable_cards(self):
        self.add_card(card_name='companies', group_type=CARD_TYPE_DATATABLE, datatable_model=Company)
        self.add_card(card_name='others', group_type=CARD_TYPE_DATATABLE, datatable_model=Company)

    def setup_table_companies(self, table, details_object):
        table.add_columns('id', 'name')
        if self.table_filter is not None:
            table.filter = self.table_filter

    def setup_table_others(self, table, details_object):
        table.add_columns('id', 'name', 'number')


def _refresh(view_cls=_TableView, **kwargs):
    view = view_cls()
    view.request = RequestFactory().post('/')
    return json.loads(view.row_refresh(**kwargs).content)


class TestRowRefresh(TestCase):

    def setUp(self):
        self.brass = Company.objects.create(name='Brass', number='7')
        self.copper = Company.objects.create(name='Copper')

    def test_the_row_comes_back_as_a_refresh_row_command(self):
        command, = _refresh(table_id='companies', row_no=f'i{self.brass.pk}')
        self.assertEqual(command['function'], 'refresh_row')
        self.assertEqual(command['row_no'], f'i{self.brass.pk}')
        self.assertEqual(command['table_id'], 'companies')
        self.assertEqual(command['data'], [self.brass.pk, 'Brass'])

    def test_the_named_table_is_the_one_read(self):
        command, = _refresh(table_id='others', row_no=f'i{self.brass.pk}')
        self.assertEqual(command['table_id'], 'others')
        self.assertEqual(command['data'], [self.brass.pk, 'Brass', '7'])

    def test_the_setup_hook_runs_once(self):
        """`setup_datatable_cards` already ran it; a second run would add every column again."""
        command, = _refresh(table_id='companies', row_no=f'i{self.brass.pk}')
        self.assertEqual(len(command['data']), 2)

    def test_with_no_table_id_the_first_table_is_read(self):
        command, = _refresh(row_no=f'i{self.copper.pk}')
        self.assertEqual(command['table_id'], 'companies')
        self.assertEqual(command['data'], [self.copper.pk, 'Copper'])

    def test_a_seq_comes_back_on_the_command(self):
        command, = _refresh(table_id='companies', row_no=f'i{self.brass.pk}', seq=4)
        self.assertEqual(command['seq'], 4)

    def test_no_seq_sent_none_returned(self):
        command, = _refresh(table_id='companies', row_no=f'i{self.brass.pk}')
        self.assertNotIn('seq', command)

    def test_a_table_filtered_by_a_q_is_narrowed_to_the_row(self):
        class QView(_TableView):
            table_filter = Q(name__startswith='B') | Q(name__startswith='C')

        command, = _refresh(QView, table_id='companies', row_no=f'i{self.copper.pk}')
        self.assertEqual(command['data'], [self.copper.pk, 'Copper'])

    def test_the_tables_own_filter_still_applies(self):
        """The row is ANDed on: a row the table filters out is not served because it was asked for."""
        class OnlyBrass(_TableView):
            table_filter = {'name': 'Brass'}

        self.assertEqual(_refresh(OnlyBrass, table_id='companies', row_no=f'i{self.copper.pk}'),
                         [{'function': 'null'}])

    def test_the_views_own_query_is_the_one_read(self):
        """A `get_<table_id>_query` is what the page's table was drawn from; a refresh reads it too."""
        class OwnQuery(_TableView):
            def get_companies_query(self, table, **kwargs):
                return table.get_query(**kwargs).exclude(name='Brass')

        self.assertEqual(_refresh(OwnQuery, table_id='companies', row_no=f'i{self.brass.pk}'),
                         [{'function': 'null'}])
        command, = _refresh(OwnQuery, table_id='companies', row_no=f'i{self.copper.pk}')
        self.assertEqual(command['data'], [self.copper.pk, 'Copper'])

    def test_nothing_to_repaint_answers_null(self):
        gone = Company.objects.create(name='Gone')
        gone_pk = gone.pk
        gone.delete()
        cases = {
            'no row_no': {'table_id': 'companies'},
            'a row_no that is not one': {'table_id': 'companies', 'row_no': 'i'},
            'a row_no in digits int() will not take': {'table_id': 'companies', 'row_no': 'i\u00b2'},
            'a row_no in another script\'s digits': {'table_id': 'companies', 'row_no': 'i\u0661'},
            'an unknown table': {'table_id': 'nope', 'row_no': f'i{self.brass.pk}'},
            'a deleted row': {'table_id': 'companies', 'row_no': f'i{gone_pk}'},
        }
        for name, kwargs in cases.items():
            with self.subTest(name):
                self.assertEqual(_refresh(**kwargs), [{'function': 'null'}])
