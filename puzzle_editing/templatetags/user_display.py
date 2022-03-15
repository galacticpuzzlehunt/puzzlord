from django import template

from puzzle_editing.models import User

register = template.Library()


@register.simple_tag
def user_display(user, linkify=False):
    """Display a user"""

    return User.html_user_display_of(user, linkify)
