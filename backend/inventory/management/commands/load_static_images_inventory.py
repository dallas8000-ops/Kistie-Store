from django.core.management.base import BaseCommand
from inventory.category_sorting import infer_category_name
from inventory.models import Category, Product
import os

STATIC_IMAGE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'core', 'static', 'core')
)

class Command(BaseCommand):
    help = 'Load products based on images in static/core/'

    def handle(self, *args, **options):
        image_files = [f for f in os.listdir(STATIC_IMAGE_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        for img in image_files:
            name = os.path.splitext(img)[0].replace('_', ' ').replace('-', ' ').title()
            category_name = infer_category_name(name)
            category, _ = Category.objects.get_or_create(
                name=category_name,
                defaults={'description': f'Auto-sorted {category_name.lower()} category'},
            )
            Product.objects.get_or_create(
                name=name,
                defaults={
                    'description': '',
                    'price_usd': 20.00,
                    'price_ugx': 74000.00,
                    'old_price': None,
                    'category': category,
                    'color': 'Multicolor',
                    'sizes': '36,38,40',
                }
            )
        self.stdout.write(self.style.SUCCESS('Products created for all static images.'))
