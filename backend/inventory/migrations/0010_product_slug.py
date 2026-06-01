from django.db import migrations, models
from django.utils.text import slugify


def populate_product_slugs(apps, schema_editor):
    Product = apps.get_model('inventory', 'Product')
    used = set()
    for product in Product.objects.order_by('id'):
        base = slugify(product.name)[:200] or f'product-{product.pk}'
        slug = base
        counter = 2
        while slug in used:
            suffix = f'-{counter}'
            slug = f'{base[: 200 - len(suffix)]}{suffix}'
            counter += 1
        used.add(slug)
        product.slug = slug
        product.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0009_ai_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='slug',
            field=models.SlugField(blank=True, max_length=220),
        ),
        migrations.RunPython(populate_product_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='product',
            name='slug',
            field=models.SlugField(blank=True, max_length=220, unique=True),
        ),
    ]
