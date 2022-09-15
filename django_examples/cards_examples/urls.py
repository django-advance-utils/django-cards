from django.urls import path

from cards_examples.views import ExampleIndex, ExampleCardsIndex

app_name = 'cards_examples'


urlpatterns = [
    path('', ExampleIndex.as_view(), name='index'),
    path('groups/', ExampleCardsIndex.as_view(), name='groups'),

]
