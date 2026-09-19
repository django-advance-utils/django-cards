"""Bootstrap class names for the example app's own markup.

A project normally names one version, because it renders for one. The examples render for
both -- the nav bar toggle flips between them on the page in front of you -- so their own
classes have to follow the request's pack the same way the cards' templates do.

Only the column float needs it today: Bootstrap 5 renamed `float-left` and `float-right` to
`float-start` and `float-end`, and card groups are laid out with them all over these views.

What cannot go through here is a class named in a class-level constant -- there is no request
at class definition time. The two that exist carry both spellings and say so; a project on one
version would simply write that version's name.
"""
from cards.packs import template_pack

FLOATS = {
    'bootstrap4': {'left': 'float-left', 'right': 'float-right'},
    'bootstrap5': {'left': 'float-start', 'right': 'float-end'},
}


def col(spec, request=None, side='left'):
    """A card group's column classes, floated the way this request's pack spells it.

        div_css_class=col('col-6', self.request)           -> 'col-6 float-left'  on 4
                                                              'col-6 float-start' on 5
        div_css_class=col('col-12', self.request, 'right') -> 'col-12 float-right' on 4
                                                              'col-12 float-end'   on 5
    """
    floats = FLOATS.get(template_pack(request), FLOATS['bootstrap4'])
    return f'{spec} {floats[side]}'
