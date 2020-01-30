from django import template

register = template.Library()

@register.inclusion_tag('tags/user_list.html')
def user_list(users):
    """Displays a QuerySet of users"""

    return {'users': users.values('username', 'profile__display_name')}
