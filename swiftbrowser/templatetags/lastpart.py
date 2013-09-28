from django import template
from django.template.defaultfilters import stringfilter
register = template.Library()


@register.filter
@stringfilter
def lastpart(value):
    value = value.strip('/').split('/')[-1]
    return value
