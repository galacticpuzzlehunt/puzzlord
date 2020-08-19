from django import template

register = template.Library()


@register.inclusion_tag("tags/puzzle_display.html")
def puzzle_display(puzzle):
    return {"puzzle": puzzle}
