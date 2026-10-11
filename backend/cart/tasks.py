from celery import shared_task

from .models import Order
from .notifications import send_order_status_notifications


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def send_order_status_notification_email(self, order_id, previous_status):
    order = Order.objects.select_related('user').get(pk=order_id)
    send_order_status_notifications(order, previous_status)
