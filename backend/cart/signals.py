from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Order
from .notifications import notify_order_status_changed


@receiver(pre_save, sender=Order)
def _cache_order_previous_status(sender, instance, **kwargs):
    if instance.pk:
        instance._previous_status = (
            Order.objects.filter(pk=instance.pk).values_list('status', flat=True).first()
        )
    else:
        instance._previous_status = None


@receiver(post_save, sender=Order)
def _order_status_changed(sender, instance, created, **kwargs):
    if created:
        return
    previous = getattr(instance, '_previous_status', None)
    if previous and previous != instance.status:
        notify_order_status_changed(instance, previous)
