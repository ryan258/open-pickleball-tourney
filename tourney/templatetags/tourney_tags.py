import uuid
from zoneinfo import ZoneInfo
from django import template
from django.utils.dateparse import parse_datetime
from django.utils.html import format_html
register = template.Library()


@register.filter
def human(value):
    return str(value or "").replace("_", " ").capitalize()


@register.filter
def money(value):
    return f"${(value or 0)/100:,.2f}"


@register.filter
def eventtime(value, zone="America/Chicago"):
    if not value:
        return "Not scheduled"
    if isinstance(value, str):
        value = parse_datetime(value)
    if not value:
        return "Not scheduled"
    return value.astimezone(ZoneInfo(zone)).strftime("%b %-d, %Y · %-I:%M %p")


@register.filter
def eventday(value, zone="America/Chicago"):
    return value.astimezone(ZoneInfo(zone)).strftime("%b %-d") if value else ""


@register.simple_tag(takes_context=True)
def action_fields(context):
    event = context.get("event")
    return format_html('<input type="hidden" name="operation_key" value="{}"><input type="hidden" name="revision" value="{}">',
                       uuid.uuid4(), event.revision if event else 0)

