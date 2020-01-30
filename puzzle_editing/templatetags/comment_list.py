from django import template
import datetime

register = template.Library()

@register.inclusion_tag('tags/comment_list.html')
def comment_list(puzzle, comments, comment_form):
    authors = set(puzzle.authors.values_list('id', flat=True))

    for comment in comments:
        comment.author.is_author = comment.author.id in authors

    return {
        'comments': comments,
        'comment_form': comment_form,
    }
