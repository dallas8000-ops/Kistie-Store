from django.core.management.base import BaseCommand

from inventory.category_sorting import DEFAULT_CATEGORY_NAME, infer_category_name
from inventory.models import Category, Product


class Command(BaseCommand):
    help = 'Auto-sort products into categories based on product names.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--include-default-only',
            action='store_true',
            help='Only update products currently assigned to the Default category.',
        )

    def handle(self, *args, **options):
        products = Product.objects.select_related('category').order_by('name')
        if options['include_default_only']:
            products = products.filter(category__name=DEFAULT_CATEGORY_NAME)

        updated = 0
        unchanged = 0

        for product in products:
            category_name = infer_category_name(product.name)
            if category_name == DEFAULT_CATEGORY_NAME:
                unchanged += 1
                continue

            if product.category and product.category.name == category_name:
                unchanged += 1
                continue

            category, _ = Category.objects.get_or_create(
                name=category_name,
                defaults={'description': f'Auto-sorted {category_name.lower()} category'},
            )
            product.category = category
            product.save(update_fields=['category'])
            updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Category sort complete. Updated {updated} product(s); left {unchanged} unchanged.'
        ))
