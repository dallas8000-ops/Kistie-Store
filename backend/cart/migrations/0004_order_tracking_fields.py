from django.db import migrations, models
from django.db.models import F


def backfill_milestone_timestamps(apps, schema_editor):
    Order = apps.get_model('cart', 'Order')
    Order.objects.filter(status='payment_confirmed').update(
        payment_confirmed_at=F('created_at'),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0003_order_orderitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='delivered_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='packed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_confirmed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='shipped_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='tracking_url',
            field=models.URLField(
                blank=True,
                help_text='Courier tracking link (shown when shipped).',
                max_length=500,
            ),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending_payment', 'Placed — pending payment'),
                    ('payment_confirmed', 'Payment received'),
                    ('packed', 'Packed'),
                    ('shipped', 'Shipped'),
                    ('delivered', 'Delivered'),
                    ('payment_failed', 'Payment failed'),
                ],
                default='pending_payment',
                max_length=20,
            ),
        ),
        migrations.RunPython(backfill_milestone_timestamps, migrations.RunPython.noop),
    ]
