import django.urls as urls
from django import template

register = template.Library()


@register.inclusion_tag("tags/nav_link.html")
def nav_link(current_path, url_name, text):
    url = urls.reverse(url_name)

    if url == "/":
        selected = current_path == url
    else:
        selected = current_path.startswith(url)

    return {
        "url": url,
        "selected": selected,
        "text": text,
        "name": url_name,
    }
