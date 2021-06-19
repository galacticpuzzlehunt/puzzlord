from django import template

from ..utils import get_upload_url

register = template.Library()


@register.filter
def upload_url(file_field):
    return get_upload_url(file_field)
