from django import template
from django.db.models import Exists
from django.db.models import Max
from django.db.models import OuterRef
from django.db.models import Subquery

from puzzle_editing.models import TestsolveParticipation
from puzzle_editing.models import User

register = template.Library()


@register.inclusion_tag("tags/testsolve_session_list.html")
def testsolve_session_list(
    sessions, user, show_notes=False, show_leave_button=False, show_ratings=False
):
    sessions = (
        sessions.annotate(
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
            last_comment_date=Max("comments__date"),
        )
        .order_by("puzzle__priority")
        .select_related("puzzle")
    )

    if show_ratings:
        part_subquery = TestsolveParticipation.objects.filter(
            session=OuterRef("pk"), user=user
        )[:1]
        sessions = sessions.annotate(
            fun_rating=Subquery(part_subquery.values("fun_rating")),
            difficulty_rating=Subquery(part_subquery.values("difficulty_rating")),
        )

    # handroll participants join to avoid queries
    # TODO: getting important tag names is also costing one query per session
    # (but that one's a lot more annoying to implement and handrolling its
    # prefetch may not be worth the performance gain)
    sessions = list(sessions)

    for session in sessions:
        session.opt_participants = []

    id_to_index = {session.id: i for i, session in enumerate(sessions)}

    for session_id, username, display_name in TestsolveParticipation.objects.filter(
        session__in=[session.id for session in sessions]
    ).values_list("session", "user__username", "user__display_name"):
        sessions[id_to_index[session_id]].opt_participants.append(
            (username, display_name)
        )

    for session in sessions:
        session.participants_html = User.html_user_list_of_flat(
            session.opt_participants, linkify=False
        )

    return {
        "sessions": sessions,
        "show_notes": show_notes,
        "show_leave": show_leave_button,
        "show_ratings": show_ratings,
    }
