"""WhatsApp click-to-chat helpers for order alerts (no Business API required)."""

from __future__ import annotations

import re
from urllib.parse import urlencode

from django.conf import settings


def store_whatsapp_number() -> str:
    """Digits only, no + prefix — for WhatsApp click-to-chat links."""
    raw = getattr(settings, 'WHATSAPP_STORE_NUMBER', '256704757198')
    raw = str(raw).strip().strip('"').strip("'")
    digits = re.sub(r'\D', '', raw)
    if digits.startswith('0') and len(digits) >= 10:
        digits = '256' + digits.lstrip('0')
    elif len(digits) == 9 and digits.startswith('7'):
        digits = '256' + digits
    return digits or '256704757198'


def format_store_phone_display(digits: str | None = None) -> str:
    """Human-readable number shown on Contact / About (matches wa.me target)."""
    digits = digits or store_whatsapp_number()
    if digits.startswith('256') and len(digits) >= 12:
        return f'+256 {digits[3:6]} {digits[6:9]} {digits[9:12]}'
    if digits:
        return f'+{digits}'
    return ''


def customer_whatsapp_digits(phone: str) -> str:
    digits = re.sub(r'\D', '', phone or '')
    if not digits:
        return ''
    if digits.startswith('0') and len(digits) >= 9:
        digits = '256' + digits.lstrip('0')
    elif len(digits) == 9 and digits[0] == '7':
        digits = '256' + digits
    return digits


def whatsapp_url(phone_digits: str, text: str) -> str:
    """
    Official click-to-chat URL (works on mobile + desktop).
    Omit ?text= when empty — a bare ?text= breaks WhatsApp on some devices.
    """
    if not phone_digits:
        return ''
    message = (text or '').strip()
    params = {'phone': phone_digits}
    if message:
        params['text'] = message
    return f'https://api.whatsapp.com/send/?{urlencode(params)}'


def staff_message_customer_url(order, message: str) -> str:
    """Open WhatsApp to the customer's number with a pre-filled message (staff sends manually)."""
    digits = customer_whatsapp_digits(order.phone)
    if not digits:
        return ''
    return whatsapp_url(digits, message)


def customer_contact_store_url(order, message: str) -> str:
    """Customer opens chat with the store."""
    return whatsapp_url(store_whatsapp_number(), message)
