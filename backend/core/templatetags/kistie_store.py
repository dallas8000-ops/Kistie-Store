from django import template

from cart.whatsapp import format_store_phone_display, store_whatsapp_number, whatsapp_url

register = template.Library()


@register.simple_tag
def whatsapp_href(message=''):
    """Full wa.me URL using WHATSAPP_STORE_NUMBER from settings."""
    return whatsapp_url(store_whatsapp_number(), message or '')


@register.simple_tag
def whatsapp_display():
    """Formatted phone shown on Contact / About (same number as wa.me links)."""
    return format_store_phone_display()
