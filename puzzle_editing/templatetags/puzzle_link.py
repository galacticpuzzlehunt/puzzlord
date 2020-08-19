from django import template

register = template.Library()


@register.inclusion_tag("tags/puzzle_link.html")
def puzzle_link(puzzle):
    return {"puzzle": puzzle}
