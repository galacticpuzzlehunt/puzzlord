import random

from django import template
from django.db.models import Exists
from django.db.models import Max
from django.db.models import OuterRef
from django.db.models import Prefetch
from django.db.models import Subquery

import puzzle_editing.status as status
from puzzle_editing.models import PuzzleTag
from puzzle_editing.models import PuzzleVisited
from puzzle_editing.models import User

register = template.Library()


def make_puzzle_data(puzzles, user, do_query_filter_in):
    puzzles = (
        puzzles.order_by("priority").annotate(
            is_spoiled=Exists(
                User.objects.filter(spoiled_puzzles=OuterRef("pk"), id=user.id)
            ),
            is_author=Exists(
                User.objects.filter(authored_puzzles=OuterRef("pk"), id=user.id)
            ),
            is_editing=Exists(
                User.objects.filter(editing_puzzles=OuterRef("pk"), id=user.id)
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
        # This prefetch is super slow.
        # .prefetch_related(
        #     Prefetch(
        #         "tags",
        #         queryset=PuzzleTag.objects.filter(important=True).only("name"),
        #         to_attr="prefetched_important_tags",
        #     ),
        # )
        .defer("description", "notes", "editor_notes", "content", "solution")
    )

    puzzles = list(puzzles)

    for puzzle in puzzles:
        puzzle.opt_authors = []
        puzzle.opt_editors = []
        puzzle.prefetched_important_tag_names = []

    puzzle_ids = [puzzle.id for puzzle in puzzles]
    id_to_index = {puzzle.id: i for i, puzzle in enumerate(puzzles)}

    # Handrolling prefetches because
    # (1) we can aggressively skip model construction
    # (2) (actually important, from my tests) if we know we're listing all
    #     puzzles, skipping the puzzles__in constraint massively improves
    #     performance. (I want to keep it in other cases so that we don't
    #     regress.)
    tagships = PuzzleTag.objects.filter(important=True)
    if do_query_filter_in:
        tagships = tagships.filter(puzzles__in=puzzle_ids)
    for tag_name, puzzle_id in tagships.values_list("name", "puzzles"):
        if puzzle_id in id_to_index:
            puzzles[id_to_index[puzzle_id]].prefetched_important_tag_names.append(
                tag_name
            )

    authorships = User.objects
    if do_query_filter_in:
        authorships = authorships.filter(authored_puzzles__in=puzzle_ids)
    for username, display_name, puzzle_id in authorships.values_list(
        "username", "display_name", "authored_puzzles"
    ):
        if puzzle_id in id_to_index:
            puzzles[id_to_index[puzzle_id]].opt_authors.append((username, display_name))

    editorships = User.objects
    if do_query_filter_in:
        editorships = editorships.filter(editing_puzzles__in=puzzle_ids)
    for username, display_name, puzzle_id in editorships.values_list(
        "username", "display_name", "editing_puzzles"
    ):
        if puzzle_id in id_to_index:
            puzzles[id_to_index[puzzle_id]].opt_editors.append((username, display_name))

    for puzzle in puzzles:
        puzzle.authors_html = User.html_user_list_of_flat(
            puzzle.opt_authors, linkify=False
        )
        puzzle.editors_html = User.html_user_list_of_flat(
            puzzle.opt_editors, linkify=False
        )

    return puzzles


# TODO: There's gotta be a better way of generating a unique ID for each time
# this template gets rendered...


@register.inclusion_tag("tags/puzzle_list.html", takes_context=True)
def puzzle_list(context, puzzles, user, with_new_link=False):
    req = context["request"]
    limit = None
    if req.method == "GET" and "limit" in req.GET:
        try:
            limit = int(req.GET["limit"])
        except ValueError:
            limit = 50

    return {
        "limit": limit,
        "puzzles": make_puzzle_data(
            puzzles, user, do_query_filter_in=req.path != "/all"
        ),
        "new_puzzle_link": False,
        "dead_status": status.DEAD,
        "deferred_status": status.DEFERRED,
        "past_needs_solution_statuses": [
            st["value"]
            for st in status.ALL_STATUSES
            if status.get_status_rank(st["value"])
            > status.get_status_rank(status.NEEDS_SOLUTION)
        ],
        "random_id": "%016x" % random.randrange(16**16),
    }
