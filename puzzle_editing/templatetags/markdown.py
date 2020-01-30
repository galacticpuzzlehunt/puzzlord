from django import template
from django.utils.safestring import mark_safe
from markdown import markdown as convert_markdown
from bleach import Cleaner
from bleach.linkifier import LinkifyFilter

register = template.Library()

SAFE_TAGS = ['a', 'abbr', 'acronym', 'b', 'big', 'blockquote', 'br', 'cite', 'code', 'dd', 'del', 'div', 'dl', 'dt', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'ins', 'li', 'ol', 'p', 'pre', 'q', 's', 'small', 'span', 'sub', 'sup', 'strike', 'strong', 'table', 'tbody', 'td', 'th', 'thead', 'tfoot', 'tr', 'u', 'ul']

# LinkifyFilter converts raw URLs in text into links
cleaner = Cleaner(tags=SAFE_TAGS, filters=[LinkifyFilter])

@register.filter
def markdown(text):
    return mark_safe(cleaner.clean(convert_markdown(text, extensions=['extra'])))
