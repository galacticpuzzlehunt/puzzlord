from collections import defaultdict

from django import template
from django.db.models import Max
from django.db.models import OuterRef
from django.db.models import Subquery

from puzzle_editing.models import TestsolveSession

register = template.Library()


def find_sessions(opt_puzzles):
    sessions = TestsolveSession.objects
    if opt_puzzles is not None:
        sessions = sessions.filter(puzzle__in=opt_puzzles)
    sessions_by_puzzle = defaultdict(list)
    for puzzle_id, *entry in sessions.values_list(
        "puzzle_id",
        "id",
        Subquery(TestsolveSession.objects.filter(id=OuterRef("pk")).values_list(Max("guesses__correct"))),
        "started",
        Subquery(TestsolveSession.objects.filter(id=OuterRef("pk")).values_list(Max("comments__date"))),
    ):
        sessions_by_puzzle[puzzle_id].append(entry)
    return sessions_by_puzzle

@register.inclusion_tag("tags/testsolve_summary.html")
def testsolve_summary(testsolves):
    sessions = []
    correct = 0
    incorrect = 0
    for session_id, is_correct, started, last_comment in testsolves:
        sessions.append(dict(
            id=session_id,
            is_correct=is_correct,
            start_date=started.date(),
            last_date=(last_comment or started).date(),
        ))
        if is_correct:
            correct += 1
        else:
            incorrect += 1
    return {
        "sessions": sessions,
        "sort_key": 100 * correct + incorrect,
    }
