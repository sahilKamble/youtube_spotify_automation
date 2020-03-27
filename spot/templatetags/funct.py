from django import template
register = template.Library()

@register.filter(name='next')
def next_value(list):
    return next(list)