from django import template
from django.contrib.auth.models import User
from django.db.models import Exists
from django.db.models import OuterRef

register = template.Library()


@register.inclusion_tag("tags/testsolve_session_list.html")
def testsolve_session_list(sessions, user, show_notes, show_leave_button):
    sessions = sessions.annotate(
        is_author=Exists(
            User.objects.filter(
                authored_puzzles__testsolve_sessions=OuterRef("pk"), id=user.id
            )
        ),
        is_spoiled=Exists(
            User.objects.filter(
                spoiled_puzzles__testsolve_sessions=OuterRef("pk"), id=user.id
            )
        ),
    ).order_by("puzzle__priority")

    return {
        "sessions": sessions,
        "show_notes": show_notes,
        "show_leave": show_leave_button,
    }
