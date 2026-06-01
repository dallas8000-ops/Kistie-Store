from decimal import Decimal
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from inventory.models import Category, Product

from .models import Cart, CartItem, Order, OrderItem
from .order_tracking import order_timeline


class CartFlowSmokeTests(TestCase):
	def setUp(self):
		category = Category.objects.create(name='Shoes', description='Footwear')
		self.product = Product.objects.create(
			name='Runner',
			description='Lightweight running shoe',
			price_usd=Decimal('49.99'),
			price_ugx=Decimal('184963.00'),
			category=category,
			color='Black',
			sizes='32,34,36',
			stock_quantity=5,
			in_stock=True,
		)

	def test_cart_page_loads(self):
		response = self.client.get(reverse('cart'))
		self.assertEqual(response.status_code, 200)

	def test_add_to_cart_creates_item(self):
		response = self.client.post(
			reverse('add_to_cart', args=[self.product.id]),
			data={'quantity': 2, 'size': '34'},
			follow=True,
		)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(CartItem.objects.count(), 1)
		item = CartItem.objects.select_related('product').first()
		self.assertEqual(item.product_id, self.product.id)
		self.assertEqual(item.quantity, 2)
		self.assertEqual(item.size, '34')

	def test_add_to_cart_rejects_invalid_size(self):
		response = self.client.post(
			reverse('add_to_cart', args=[self.product.id]),
			data={'quantity': 1, 'size': 'XL'},
		)
		self.assertEqual(response.status_code, 302)
		self.assertTrue(
			response.url == reverse('shop')
			or response.url == reverse('product_detail', args=[self.product.slug])
		)
		self.assertEqual(CartItem.objects.count(), 0)

	def test_checkout_creates_order_and_clears_cart(self):
		self.client.post(
			reverse('add_to_cart', args=[self.product.id]),
			data={'quantity': 2, 'size': '34'},
		)

		response = self.client.post(
			reverse('checkout'),
			data={
				'name': 'Barney Tester',
				'phone': '+256700000000',
				'country': 'Uganda',
				'notes': 'Deliver after 5 PM',
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(Order.objects.count(), 1)
		self.assertEqual(OrderItem.objects.count(), 1)
		self.assertEqual(CartItem.objects.count(), 0)
		self.product.refresh_from_db()
		self.assertEqual(self.product.stock_quantity, 3)

	def test_add_to_cart_rejects_quantity_above_stock(self):
		response = self.client.post(
			reverse('add_to_cart', args=[self.product.id]),
			data={'quantity': 99, 'size': '34'},
		)

		self.assertEqual(response.status_code, 302)
		self.assertTrue(
			response.url == reverse('shop')
			or response.url == reverse('product_detail', args=[self.product.slug])
		)
		self.assertEqual(CartItem.objects.count(), 0)

	def test_update_cart_item_rejects_quantity_above_stock(self):
		self.client.post(
			reverse('add_to_cart', args=[self.product.id]),
			data={'quantity': 1, 'size': '34'},
		)

		item = CartItem.objects.get()
		response = self.client.post(
			reverse('update_cart_item', args=[item.id]),
			data={'quantity': 10},
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse('cart'))
		item.refresh_from_db()
		self.assertEqual(item.quantity, 1)

	def test_cart_view_cleans_stale_empty_guest_carts(self):
		stale = Cart.objects.create(user=None, session_key='old-empty')
		Cart.objects.filter(id=stale.id).update(created_at=timezone.now() - timedelta(days=8))

		active = Cart.objects.create(user=None, session_key='active-cart')
		CartItem.objects.create(cart=active, product=self.product, quantity=1, size='34', color='Black')

		response = self.client.get(reverse('cart'))
		self.assertEqual(response.status_code, 200)
		self.assertFalse(Cart.objects.filter(id=stale.id).exists())
		self.assertTrue(Cart.objects.filter(id=active.id).exists())


class OrderTrackingTests(TestCase):
	def setUp(self):
		category = Category.objects.create(name='Dresses', description='')
		self.product = Product.objects.create(
			name='Timeline Dress',
			description='Test',
			price_usd=Decimal('80.00'),
			price_ugx=Decimal('0'),
			category=category,
			stock_quantity=2,
			sizes='38',
		)

	def _place_order(self):
		self.client.post(
			reverse('add_to_cart', args=[self.product.id]),
			data={'quantity': 1, 'size': '38'},
		)
		return self.client.post(
			reverse('checkout'),
			data={
				'name': 'Jane Guest',
				'phone': '+256701234567',
				'country': 'Uganda',
				'notes': '',
			},
		)

	def test_checkout_success_shows_timeline(self):
		response = self._place_order()
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'order-timeline')
		self.assertContains(response, 'Track this order')

	def test_status_progression_sets_timestamps(self):
		order = Order.objects.create(
			customer_name='Test',
			phone='+256700',
			country='Uganda',
			payment_method='mtn',
			currency='USD',
			total_amount=Decimal('10.00'),
		)
		order.status = Order.STATUS_CONFIRMED
		order.save()
		order.refresh_from_db()
		self.assertIsNotNone(order.payment_confirmed_at)

		order.status = Order.STATUS_SHIPPED
		order.tracking_url = 'https://example.com/track/123'
		order.save()
		order.refresh_from_db()
		self.assertIsNotNone(order.shipped_at)

		steps = order_timeline(order)
		shipped = next(s for s in steps if s['key'] == 'shipped')
		self.assertTrue(shipped['show_tracking'])

	def test_guest_can_track_order_with_phone(self):
		self._place_order()
		order = Order.objects.get()
		response = self.client.post(
			reverse('order_track'),
			data={'order_ref': order.order_ref, 'phone': '0701234567'},
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, order.order_ref)
		self.assertContains(response, 'order-timeline')

	def test_track_rejects_wrong_phone(self):
		self._place_order()
		order = Order.objects.get()
		response = self.client.post(
			reverse('order_track'),
			data={'order_ref': order.order_ref, 'phone': '9999999999'},
		)
		self.assertEqual(response.status_code, 200)
		self.assertNotContains(response, 'order-timeline')
