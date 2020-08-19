import datetime

from django import template
from django.conf import settings

register = template.Library()


def display_timedelta(delta):
    """convert a timedelta to a human-readable format"""

    days = ""
    if delta.days:
        if delta.days == 1:
            days = "1 day, "
        else:
            days = "{} days, ".format(delta.days)
    return days + "{}:{:02}:{:02}".format(
        delta.seconds // 3600, delta.seconds % 3600 // 60, delta.seconds % 60
    )


@register.inclusion_tag("tags/countdown.html")
def countdown():
    delta = settings.HUNT_TIME - datetime.datetime.now(datetime.timezone.utc)
    countdown = delta >= datetime.timedelta(0)
    return {
        "countdown": countdown,
        "delta": display_timedelta(abs(delta)),
    }
