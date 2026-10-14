from decimal import Decimal, InvalidOperation

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def inr(value, decimals="auto"):
    """12345.5 -> ₹12,345.50 using Indian digit grouping."""
    try:
        d = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return ""
    show = decimals == "2" or (decimals == "auto" and d != d.to_integral_value())
    s = f"{abs(d):.2f}" if show else f"{abs(d):.0f}"
    whole, _, frac = s.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts) + "," + tail
    out = "₹" + whole + ("." + frac if frac else "")
    return "-" + out if d < 0 else out


@register.filter
def stars(rating):
    try:
        r = float(rating or 0)
    except (TypeError, ValueError):
        r = 0
    full = int(round(r))
    on = "★" * full
    off = "★" * (5 - full)
    return format_html('<span class="stars" role="img" aria-label="{} out of 5 stars">{}<span class="off">{}</span></span>', f"{r:g}", on, mark_safe(off))


@register.filter
def field_class(field):
    return field.field.widget.__class__.__name__.lower()


@register.simple_tag(takes_context=True)
def qs_with(context, **kwargs):
    params = context["request"].GET.copy()
    for k, v in kwargs.items():
        params[k] = v
    return params.urlencode()
