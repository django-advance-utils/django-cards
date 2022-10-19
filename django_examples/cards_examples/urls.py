from django.urls import path, register_converter
from cards.url_converters import CardListConverter


from cards_examples.views import ExampleIndex, ExampleCardsIndex, ExampleCompanyCardList, ExampleCompanyCardAdvancedList

app_name = 'cards_examples'


register_converter(CardListConverter, 'card_list')

urlpatterns = [
    path('', ExampleIndex.as_view(), name='index'),
    path('groups/', ExampleCardsIndex.as_view(), name='groups'),
    path('list/<card_list:slug>', ExampleCompanyCardList.as_view(), name='list'),
    path('list/adv/<card_list:slug>', ExampleCompanyCardAdvancedList.as_view(), name='list_adv'),
]
