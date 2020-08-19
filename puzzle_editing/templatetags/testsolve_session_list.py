from django import template
from django.contrib.auth.models import User

register = template.Library()


@register.inclusion_tag("tags/testsolve_session_list.html")
def testsolve_session_list(sessions, show_notes, show_leave_button):
    return {
        "sessions": sessions.order_by("puzzle__priority"),
        "show_notes": show_notes,
        "show_leave": show_leave_button,
    }
