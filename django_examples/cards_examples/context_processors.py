import os

from django.conf import settings

SESSION_KEY = 'cards_example_bootstrap'
SUPPORTED = ('4', '5')


def bootstrap_version(request):
    """Which Bootstrap the example app should load, and the link that flips it.

    django-cards renders for Bootstrap 4 and Bootstrap 5 from one set of templates by
    emitting both spellings of every class and data attribute. That is only worth anything
    if someone can look at both, so the examples serve either -- and the useful way to look
    is to flip back and forth on the page in front of you, not to restart the server. So the
    choice lives in the session, and `?bootstrap=5` on any URL sets it:

        http://localhost:8000/treegrid/?bootstrap=5

    The nav bar carries a toggle that does exactly that. `CARDS_EXAMPLE_BOOTSTRAP=5` in the
    environment (or in settings) still sets the starting point for a fresh session.

    Bootstrap 4 stays the default, because that is what the rest of the stack -- django-menus,
    django-modals, django-datatables, crispy's template pack -- still emits. Under 5 those
    libraries' own markup is not yet dual, so parts of the page outside the cards will look
    wrong. That is the point of having the switch: it shows what is left to do.
    """
    requested = request.GET.get('bootstrap')
    if requested in SUPPORTED and hasattr(request, 'session'):
        request.session[SESSION_KEY] = requested

    version = None
    if hasattr(request, 'session'):
        version = request.session.get(SESSION_KEY)
    if version not in SUPPORTED:
        version = getattr(settings, 'CARDS_EXAMPLE_BOOTSTRAP', None)
    if version is None:
        version = os.environ.get('CARDS_EXAMPLE_BOOTSTRAP', '4')
    version = str(version)
    if version not in SUPPORTED:
        version = '4'

    other = '5' if version == '4' else '4'
    # Keep whatever else is on the URL, so the toggle does not drop a page's own query string.
    params = request.GET.copy()
    params['bootstrap'] = other
    return {
        'bootstrap_version': version,
        'bootstrap_other_version': other,
        'bootstrap_toggle_url': f'{request.path}?{params.urlencode()}',
    }
