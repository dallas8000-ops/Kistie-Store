from django.db import migrations, models
from django.utils.text import slugify


def populate_product_slugs(apps, schema_editor):
    Product = apps.get_model('inventory', 'Product')
    used = set()
    for product in Product.objects.order_by('id'):
        existing = getattr(product, 'slug', None) or ''
        if existing:
            used.add(existing)
            continue
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


def ensure_slug_schema(apps, schema_editor):
    """Idempotent slug column + indexes (safe after partial failed deploys on PostgreSQL)."""
    connection = schema_editor.connection
    vendor = connection.vendor

    if vendor == 'postgresql':
        schema_editor.execute(
            'ALTER TABLE inventory_product '
            'ADD COLUMN IF NOT EXISTS slug varchar(220) NOT NULL DEFAULT \'\''
        )
    elif vendor == 'sqlite':
        with connection.cursor() as cursor:
            columns = {
                row[1]
                for row in cursor.execute('PRAGMA table_info(inventory_product)').fetchall()
            }
        if 'slug' not in columns:
            schema_editor.execute(
                'ALTER TABLE inventory_product '
                "ADD COLUMN slug varchar(220) NOT NULL DEFAULT ''"
            )
    else:
        Product = apps.get_model('inventory', 'Product')
        field = Product._meta.get_field('slug')
        schema_editor.add_field(
            Product,
            field,
        )

    populate_product_slugs(apps, schema_editor)

    if vendor == 'postgresql':
        # Names match Django's SlugField unique indexes on PostgreSQL.
        schema_editor.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS inventory_product_slug_40cd5b78_uniq '
            'ON inventory_product (slug)'
        )
        schema_editor.execute(
            'CREATE INDEX IF NOT EXISTS inventory_product_slug_40cd5b78_like '
            'ON inventory_product (slug varchar_pattern_ops)'
        )
    elif vendor == 'sqlite':
        with connection.cursor() as cursor:
            indexes = {
                row[0]
                for row in cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' "
                    "AND tbl_name='inventory_product'"
                ).fetchall()
            }
        if 'inventory_product_slug_40cd5b78_uniq' not in indexes:
            schema_editor.execute(
                'CREATE UNIQUE INDEX inventory_product_slug_40cd5b78_uniq '
                'ON inventory_product (slug)'
            )


def reverse_slug_schema(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor == 'postgresql':
        schema_editor.execute('DROP INDEX IF EXISTS inventory_product_slug_40cd5b78_like')
        schema_editor.execute('DROP INDEX IF EXISTS inventory_product_slug_40cd5b78_uniq')
        schema_editor.execute('ALTER TABLE inventory_product DROP COLUMN IF EXISTS slug')
    elif connection.vendor == 'sqlite':
        schema_editor.execute('DROP INDEX IF EXISTS inventory_product_slug_40cd5b78_uniq')
        # SQLite < 3.35 cannot DROP COLUMN easily; leave column on rollback in dev.


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0009_ai_fields'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='product',
                    name='slug',
                    field=models.SlugField(blank=True, max_length=220, unique=True),
                ),
            ],
            database_operations=[
                migrations.RunPython(ensure_slug_schema, reverse_slug_schema),
            ],
        ),
    ]
