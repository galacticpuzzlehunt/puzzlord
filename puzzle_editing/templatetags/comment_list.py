import datetime

from django import template

import puzzle_editing.status as status
from puzzle_editing.models import CommentReaction

register = template.Library()


@register.inclusion_tag("tags/comment_list.html")
def comment_list(
    user,
    puzzle,
    comments,
    comment_form,
    show_testsolve_session_links,
    allow_status_changes,
):
    comments = comments.order_by("date").select_related("author__profile")

    authors = set(puzzle.authors.values_list("id", flat=True))

    for comment in comments:
        comment.author.is_author = comment.author.id in authors
        comment.author.is_current_user = comment.author.id == user.id
        # as much as I wish we could use a collections.defaultdict(list),
        # it's more annoying...
        # https://stackoverflow.com/questions/4764110/django-template-cant-loop-defaultdict
        comment.merged_reactions = dict()

    # we'll mutate through this!!
    ref_comment_by_id = {comment.id: comment for comment in comments}
    # handrolling a merge; there can be lots of comments in a thread but should
    # be relatively few reactions
    reactions = CommentReaction.objects.filter(
        comment__in=[comment.id for comment in comments]
    ).select_related("reactor")
    for reaction in reactions:
        mr = ref_comment_by_id[reaction.comment_id].merged_reactions
        if reaction.emoji not in mr:
            mr[reaction.emoji] = []
        mr[reaction.emoji].append(reaction.reactor.username)

    return {
        "username": user.username,
        "puzzle": puzzle,
        "comments": comments,
        "comment_form": comment_form,
        "show_testsolve_session_links": show_testsolve_session_links,
        "allow_status_changes": allow_status_changes,
        "all_statuses": status.ALL_STATUSES,
        "emoji_options": CommentReaction.EMOJI_OPTIONS,
    }
