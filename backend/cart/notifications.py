"""Email + WhatsApp click-to-chat alerts when order status changes."""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from .models import Order
from .whatsapp import (
    customer_contact_store_url,
    staff_message_customer_url,
    store_whatsapp_number,
)

logger = logging.getLogger(__name__)

_STATUS_LABELS = dict(Order.STATUS_CHOICES)


def order_notification_recipient(order):
    email = (order.customer_email or '').strip()
    if email:
        return email
    if order.user_id and order.user.email:
        return order.user.email.strip()
    return ''


def _staff_alert_email():
    return (
        getattr(settings, 'ORDER_ALERT_EMAIL', '')
        or getattr(settings, 'CONTACT_RECIPIENT_EMAIL', '')
        or ''
    ).strip()


def _track_order_url(order_ref):
    base = (getattr(settings, 'SITE_URL', '') or '').rstrip('/')
    path = reverse('order_track')
    qs = f'?order_ref={order_ref}'
    if base:
        return f'{base}{path}{qs}'
    return f'{path}{qs}'


def _notify_customer_email(order, previous_status, label, track_url):
    recipient = order_notification_recipient(order)
    if not recipient:
        logger.info(
            'Skipping order status email for %s (no customer email on file)',
            order.order_ref,
        )
        return

    subject = f'Kistie Store — order {order.order_ref} update: {label}'

    lines = [
        f'Hello {order.customer_name},',
        '',
        f'Your order {order.order_ref} is now: {label}.',
        '',
    ]
    if order.status == Order.STATUS_SHIPPED and order.tracking_url:
        lines.extend([
            f'Tracking link: {order.tracking_url}',
            '',
        ])

    wa_text = (
        f'Hi, I have a question about my order {order.order_ref} ({label}).'
    )
    wa_url = customer_contact_store_url(order, wa_text)
    if wa_url:
        lines.extend([
            f'Questions? Message us on WhatsApp: {wa_url}',
            '',
        ])

    lines.extend([
        f'Track your order anytime: {track_url}',
        '',
        'Thank you for shopping with Kistie Store.',
        '— Kampala team',
    ])
    body = '\n'.join(lines)

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception:
        logger.exception('Failed to send order status email for %s', order.order_ref)


def _notify_staff_email(order, previous_status, label, track_url):
    staff_email = _staff_alert_email()
    if not staff_email:
        return

    prev_label = _STATUS_LABELS.get(previous_status, previous_status)
    subject = f'[Kistie] Order {order.order_ref} → {label}'

    customer_wa_msg = (
        f'Hi {order.customer_name}, your Kistie Store order {order.order_ref} '
        f'is now: {label}.'
    )
    if order.status == Order.STATUS_SHIPPED:
        customer_wa_msg += ' Your package is on the way.'
        if order.tracking_url:
            customer_wa_msg += f' Track here: {order.tracking_url}'

    staff_to_customer = staff_message_customer_url(order, customer_wa_msg)

    lines = [
        f'Order {order.order_ref} changed: {prev_label} → {label}',
        '',
        f'Customer: {order.customer_name}',
        f'Phone: {order.phone}',
        f'Country: {order.country}',
        f'Total: {order.currency} {order.total_amount}',
        '',
        f'Admin track page: {track_url}',
        '',
    ]
    if staff_to_customer:
        lines.extend([
            'WhatsApp — tap to message the customer (you still press Send in WhatsApp):',
            staff_to_customer,
            '',
        ])
    else:
        lines.append('No valid customer phone for WhatsApp link.')
        lines.append('')

    lines.append(f'Store WhatsApp: https://wa.me/{store_whatsapp_number()}')

    try:
        send_mail(
            subject=subject,
            message='\n'.join(lines),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[staff_email],
            fail_silently=False,
        )
    except Exception:
        logger.exception('Failed to send staff order alert for %s', order.order_ref)


def notify_order_status_changed(order, previous_status):
    """Email customer (if possible) and staff with WhatsApp deep links."""
    if previous_status == order.status:
        return

    label = _STATUS_LABELS.get(order.status, order.status)
    track_url = _track_order_url(order.order_ref)

    _notify_customer_email(order, previous_status, label, track_url)
    _notify_staff_email(order, previous_status, label, track_url)
