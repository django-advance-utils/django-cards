"""The card factories that derive ``show_header`` must still let a caller say it.

``add_accordion_card``, ``add_iframe_card`` and ``add_treegrid_card`` set ``show_header`` from the
title rather than taking it from the caller, and passed it positionally alongside ``**kwargs``, so
``add_treegrid_card(show_header=True)`` raised ``TypeError: got multiple values``. That was
invisible while the templates' header guard read ``show_header and title or menu``, because a menu
drew a header whatever ``show_header`` said. With the guard nested, a titleless card with a menu
has nowhere to render it -- ``card.menu`` appears inside the header block and nowhere else -- and
no way to ask for one either.

So: the derived default keeps a header where there is a menu to put in it, and the caller can
override the default in both directions.

Accordion is the exception, and is asserted as one. Its template draws the header on
``show_header`` alone, so a menu is not a reason for one and its default stays tied to the title;
what it gains here is only the override.
"""
from cards.standard import CardMixin
from django.test import RequestFactory, SimpleTestCase
from django.views.generic import TemplateView
from django_menus.menu import AjaxButtonMenuItem, HtmlMenu

MENU_LABEL = 'Do a thing'

#: Factory name -> the arguments it needs beyond title and menu.
DERIVED = {
    'add_iframe_card': {'iframe_url': 'https://example.com'},
    'add_treegrid_card': {},
}


class _CardView(CardMixin, TemplateView):
    pass


def _view():
    view = _CardView()
    view.request = RequestFactory().get('/')
    return view


def _menu(view):
    return HtmlMenu(view.request, 'button_group').add_items(
        AjaxButtonMenuItem(button_name='do_a_thing', menu_display=MENU_LABEL))


def _card(factory, name, **kwargs):
    view = _view()
    if kwargs.pop('with_menu', False):
        kwargs['menu'] = _menu(view)
    return getattr(view, factory)(card_name=name, **DERIVED[factory], **kwargs)


class TestDerivedShowHeader(SimpleTestCase):
    def test_a_titleless_card_with_a_menu_keeps_its_menu(self):
        """The regression: the menu renders in the header, so no header means no menu."""
        for factory in DERIVED:
            with self.subTest(factory=factory):
                card = _card(factory, 'probe', title=None, with_menu=True)
                self.assertTrue(card.show_header)
                self.assertIn(MENU_LABEL, card.render())

    def test_a_titleless_card_with_nothing_to_show_draws_no_header(self):
        for factory in DERIVED:
            with self.subTest(factory=factory):
                card = _card(factory, 'probe', title=None)
                self.assertFalse(card.show_header)
                self.assertNotIn('card-header', card.render())

    def test_a_title_still_asks_for_a_header(self):
        for factory in DERIVED:
            with self.subTest(factory=factory):
                self.assertTrue(_card(factory, 'probe', title='Titled').show_header)


class TestShowHeaderOverride(SimpleTestCase):
    """A caller saying it outright wins over whatever the factory would derive."""

    def test_show_header_can_be_passed(self):
        for factory in DERIVED:
            for asked in (True, False):
                with self.subTest(factory=factory, show_header=asked):
                    card = _card(factory, 'probe', title='Titled', show_header=asked)
                    self.assertIs(card.show_header, asked)

    def test_show_header_off_suppresses_the_header_of_a_card_with_a_menu(self):
        for factory in DERIVED:
            with self.subTest(factory=factory):
                card = _card(factory, 'probe', title='Titled', with_menu=True, show_header=False)
                self.assertNotIn('card-header', card.render())

    def test_show_header_on_does_not_conjure_a_header_with_nothing_in_it(self):
        """The switch permits a header; the template still asks what would go in one."""
        for factory in DERIVED:
            with self.subTest(factory=factory):
                card = _card(factory, 'probe', title=None, show_header=True)
                self.assertTrue(card.show_header)
                self.assertNotIn('card-header', card.render())


class TestAccordionShowHeader(SimpleTestCase):
    """Accordion derives from the title alone, and now takes an override too."""

    def test_a_menu_is_not_a_reason_for_a_header(self):
        view = _view()
        card = view.add_accordion_card(card_name='acc', title=None, menu=_menu(view))
        self.assertFalse(card.show_header)

    def test_show_header_can_be_passed(self):
        view = _view()
        card = view.add_accordion_card(card_name='acc', title=None, menu=_menu(view),
                                       show_header=True)
        self.assertTrue(card.show_header)
        self.assertIn(MENU_LABEL, card.render())
