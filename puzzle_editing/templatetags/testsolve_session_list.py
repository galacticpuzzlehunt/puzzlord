from django import template
from django.contrib.auth.models import User

register = template.Library()

@register.inclusion_tag('tags/testsolve_session_list.html')
def testsolve_session_list(sessions):
    return {'sessions': sessions.order_by('puzzle__priority')}
