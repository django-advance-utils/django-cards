import os

from django.conf import settings


def bootstrap_version(request):
    """Which Bootstrap the example app should load.

    django-cards renders for Bootstrap 4 and Bootstrap 5 from one set of templates by
    emitting both spellings of every class and data attribute. That is only worth anything
    if someone can look at both, so the examples can be served either way:

        CARDS_EXAMPLE_BOOTSTRAP=5 python manage.py runserver

    Bootstrap 4 stays the default, because that is what the rest of the stack -- django-menus,
    django-modals, django-datatables, crispy's template pack -- still emits. Under 5 those
    libraries' own markup is not yet dual, so parts of the page outside the cards will look
    wrong. That is the point of having the switch: it shows what is left to do.
    """
    version = getattr(settings, 'CARDS_EXAMPLE_BOOTSTRAP', None)
    if version is None:
        version = os.environ.get('CARDS_EXAMPLE_BOOTSTRAP', '4')
    return {'bootstrap_version': str(version)}
