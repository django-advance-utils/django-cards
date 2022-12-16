from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def show_card(card, override_card_context=None):
    if override_card_context is None or override_card_context == '':
        html = card.render()
    else:
        html = card.render(override_card_context)
    return mark_safe(html)
