from django import template

from puzzle_editing.models import UserProfile

register = template.Library()


@register.inclusion_tag("tags/user_display.html")
def user_display(user):
    """Display a user"""

    try:
        if user.profile.display_name:
            user.display_name = user.profile.display_name
    except UserProfile.DoesNotExist:
        pass

    return {"user": user}
