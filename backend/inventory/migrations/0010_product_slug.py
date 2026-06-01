from django.db import migrations, models
from django.utils.text import slugify


def populate_product_slugs(apps, schema_editor):
    """Write slugs via SQL — historical Product in database_operations has no slug field yet."""
    Product = apps.get_model('inventory', 'Product')
    connection = schema_editor.connection

    used = set()
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT slug FROM inventory_product WHERE slug IS NOT NULL AND slug != ''"
        )
        used = {row[0] for row in cursor.fetchall()}

    with connection.cursor() as cursor:
        for product_id, name in Product.objects.order_by('id').values_list('id', 'name'):
            cursor.execute('SELECT slug FROM inventory_product WHERE id = %s', [product_id])
            existing = (cursor.fetchone() or [''])[0]
            if existing:
                used.add(existing)
                continue

            base = slugify(name)[:200] or f'product-{product_id}'
            slug = base
            counter = 2
            while slug in used:
                suffix = f'-{counter}'
                slug = f'{base[: 200 - len(suffix)]}{suffix}'
                counter += 1
            used.add(slug)
            cursor.execute(
                'UPDATE inventory_product SET slug = %s WHERE id = %s',
                [slug, product_id],
            )


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
