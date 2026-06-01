from decimal import Decimal

from django.test import TestCase

from core.shop_search import parse_search_query, search_hint_label, smart_shop_search
from inventory.models import Category, Product


class ShopSearchParseTests(TestCase):
    def test_parses_color_size_and_terms(self):
        parsed = parse_search_query('blue dress size 38')
        self.assertEqual(parsed['eu_size'], '38')
        self.assertIn('blue', parsed['colors'])
        self.assertTrue(any('dress' in t for t in parsed['terms']) or not parsed['terms'])

    def test_parses_max_price(self):
        parsed = parse_search_query('red top under 80')
        self.assertIn('red', parsed['colors'])
        self.assertEqual(parsed['max_price_usd'], 80.0)


class ShopSearchFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cat = Category.objects.create(name='Dresses', description='')
        cls.vest = Product.objects.create(
            name='Navy Check Vest',
            description='Layering piece',
            price_usd=Decimal('80'),
            price_ugx=Decimal('0'),
            category=cat,
            color='navy',
            stock_quantity=3,
            sizes='38,40',
        )
        cls.dress = Product.objects.create(
            name='Blue Summer Dress',
            description='Light cotton',
            price_usd=Decimal('120'),
            price_ugx=Decimal('0'),
            category=cat,
            color='blue',
            stock_quantity=2,
            sizes='36,38',
        )

    def test_smart_search_filters_by_color_and_size(self):
        qs = Product.objects.all()
        filtered, parsed = smart_shop_search(qs, 'blue dress size 38')
        names = list(filtered.values_list('name', flat=True))
        self.assertIn(self.dress.name, names)
        self.assertNotIn(self.vest.name, names)
        self.assertIn('38', parsed['eu_size'])

    def test_search_hint_label(self):
        parsed = parse_search_query('magenta size 40')
        label = search_hint_label(parsed)
        self.assertIn('magenta', label)
        self.assertIn('EU 40', label)
