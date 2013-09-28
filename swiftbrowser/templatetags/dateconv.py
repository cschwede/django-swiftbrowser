from datetime import datetime
from django import template
from django.template.defaultfilters import stringfilter
from django.utils.timezone import utc
register = template.Library()


@register.filter
@stringfilter
def dateconv(value):
    try:
        value = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")
        value = value.replace(tzinfo=utc)
    except ValueError:
        value = 0.0
    return value
