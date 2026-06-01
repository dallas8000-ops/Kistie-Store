from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0004_order_tracking_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='customer_email',
            field=models.EmailField(
                blank=True,
                help_text='Optional — used for order status updates.',
                max_length=254,
            ),
        ),
    ]
