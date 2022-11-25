from django.urls import path, register_converter
from cards.url_converters import CardListConverter
from cards_examples.views.base import HelloModal
from cards_examples.views.list import ExampleCompanyCardList, ExampleCompanyCardAdvancedList
from cards_examples.views.main import ExampleIndex, ExampleCardsIndex
from cards_examples.views.tree import ExampleCompanyTree
from cards_examples.views.datatable import DatatableExample

from cards_examples.views.child_cards import ChildCardExampleIndex

app_name = 'cards_examples'


register_converter(CardListConverter, 'card_list')

urlpatterns = [
    path('', ExampleIndex.as_view(), name='index'),
    path('hello_modal/', HelloModal.as_view(), name='hello_modal'),

    path('groups/', ExampleCardsIndex.as_view(), name='groups'),

    path('list/<card_list:slug>', ExampleCompanyCardList.as_view(), name='list'),
    path('list/adv/<card_list:slug>', ExampleCompanyCardAdvancedList.as_view(), name='list_adv'),

    path('tree/<card_list:slug>', ExampleCompanyTree.as_view(), name='tree'),

    path('child-cards/', ChildCardExampleIndex.as_view(), name='child_cards'),

    path('datatable/', DatatableExample.as_view(), name='datatable'),
]


