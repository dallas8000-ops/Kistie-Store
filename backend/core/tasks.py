import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def send_contact_inquiry_email(self, inquiry_data):
    send_mail(
        subject=f"New storefront inquiry: {inquiry_data['subject']}",
        message=(
            f"Name: {inquiry_data['name']}\n"
            f"Email: {inquiry_data['email']}\n\n"
            f"Message:\n{inquiry_data['message']}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.CONTACT_RECIPIENT_EMAIL],
        fail_silently=False,
    )
    logger.info('Queued contact inquiry email delivered for %s', inquiry_data['email'])
