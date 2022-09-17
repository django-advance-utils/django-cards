from django.urls.converters import StringConverter


class CardListConverter(StringConverter):
    regex = '[^/]*'
