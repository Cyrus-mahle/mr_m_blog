import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import Truncator

register = template.Library()


@register.filter
def format_post(text):
    """
    Turn plain post text into safe HTML.
      blank line   -> new paragraph
      "## Heading" -> <h2>
      "- item"     -> bullet list
    EVERY piece of user text goes through escape() first, so a hacker's
    <script> is shown as text and never runs (XSS protection).
    """
    blocks = re.split(r"\n\s*\n", str(text).replace("\r\n", "\n").strip())
    out = []
    for block in blocks:
        lines = [ln.rstrip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        if len(lines) == 1 and lines[0].startswith("## "):
            out.append("<h2>%s</h2>" % escape(lines[0][3:]))
        elif all(ln.startswith("- ") for ln in lines):
            items = "".join("<li>%s</li>" % escape(ln[2:]) for ln in lines)
            out.append("<ul>%s</ul>" % items)
        else:
            out.append("<p>%s</p>" % "<br>".join(escape(ln) for ln in lines))
    return mark_safe("".join(out))  # safe: everything above was escaped


@register.filter
def excerpt(text, words=35):
    """Short plain-text preview (the template escapes it)."""
    plain = re.sub(r"^(## |- )", "", str(text), flags=re.M)
    return Truncator(plain).words(int(words))