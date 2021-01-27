import datetime

from django import template

register = template.Library()


@register.inclusion_tag("tags/comment_list.html")
def comment_list(user, puzzle, comments, comment_form, show_testsolve_session_links):
    comments = comments.order_by("date").select_related("author__profile")

    authors = set(puzzle.authors.values_list("id", flat=True))

    for comment in comments:
        comment.author.is_author = comment.author.id in authors
        comment.author.is_current_user = comment.author.id == user.id

    return {
        "comments": comments,
        "comment_form": comment_form,
        "show_testsolve_session_links": show_testsolve_session_links,
    }
