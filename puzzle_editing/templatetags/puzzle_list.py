import random

from django import template
from django.contrib.auth.models import User
from django.db.models import Exists
from django.db.models import Max
from django.db.models import OuterRef
from django.db.models import Subquery

import puzzle_editing.status as status
from puzzle_editing.models import PuzzleTag
from puzzle_editing.models import PuzzleVisited

register = template.Library()


def make_puzzle_data(puzzles, user):
    return (
        puzzles.order_by("priority")
        .prefetch_related("authors__profile", "discussion_editors__profile", "tags")
        .annotate(
            is_spoiled=Exists(
                User.objects.filter(spoiled_puzzles=OuterRef("pk"), id=user.id)
            ),
            is_author=Exists(
                User.objects.filter(authored_puzzles=OuterRef("pk"), id=user.id)
            ),
            is_discussing=Exists(
                User.objects.filter(discussing_puzzles=OuterRef("pk"), id=user.id)
            ),
            is_factchecking=Exists(
                User.objects.filter(factchecking_puzzles=OuterRef("pk"), id=user.id)
            ),
            is_postprodding=Exists(
                User.objects.filter(postprodding_puzzles=OuterRef("pk"), id=user.id)
            ),
            last_comment_date=Max("comments__date"),
            last_visited_date=Subquery(
                PuzzleVisited.objects.filter(puzzle=OuterRef("pk"), user=user).values(
                    "date"
                )
            ),
        )
    )


# TODO: There's gotta be a better way of generating a unique ID for each time
# this template gets rendered...


@register.inclusion_tag("tags/puzzle_list.html")
def puzzle_list(puzzles, user):
    return {
        "puzzles": make_puzzle_data(puzzles, user),
        "new_puzzle_link": False,
        "dead_status": status.DEAD,
        "deferred_status": status.DEFERRED,
        "random_id": "%016x" % random.randrange(16 ** 16),
    }


@register.inclusion_tag("tags/puzzle_list.html")
def puzzle_list_with_new_link(puzzles, user):
    return {
        "puzzles": make_puzzle_data(puzzles, user),
        "new_puzzle_link": True,
        "dead_status": status.DEAD,
        "deferred_status": status.DEFERRED,
        "random_id": "%016x" % random.randrange(16 ** 16),
    }
