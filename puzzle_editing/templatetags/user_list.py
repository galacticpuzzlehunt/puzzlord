from django import template

from puzzle_editing.models import UserProfile

register = template.Library()


@register.simple_tag
def user_list(users, linkify=False, skip_optimize=False):
    """Displays a QuerySet of users"""

    if not skip_optimize:
        users = users.select_related("profile").only(
            "username", "profile__display_name"
        )

    return UserProfile.html_user_list_of(users, linkify)
