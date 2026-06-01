"""Email shoppers when order status changes (requires customer_email or user email)."""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from .models import Order

logger = logging.getLogger(__name__)

_STATUS_LABELS = dict(Order.STATUS_CHOICES)


def order_notification_recipient(order):
    email = (order.customer_email or '').strip()
    if email:
        return email
    if order.user_id and order.user.email:
        return order.user.email.strip()
    return ''


def _track_order_url(order_ref):
    base = (getattr(settings, 'SITE_URL', '') or '').rstrip('/')
    path = reverse('order_track')
    qs = f'?order_ref={order_ref}'
    if base:
        return f'{base}{path}{qs}'
    return f'{path}{qs}'


def notify_order_status_changed(order, previous_status):
    """Send a plain-text update when staff changes order.status."""
    if previous_status == order.status:
        return

    recipient = order_notification_recipient(order)
    if not recipient:
        logger.info(
            'Skipping order status email for %s (no customer email on file)',
            order.order_ref,
        )
        return

    label = _STATUS_LABELS.get(order.status, order.status)
    track_url = _track_order_url(order.order_ref)
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
