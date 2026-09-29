import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.urls import reverse

from core import views as core_views
from inventory.models import Category, Product

from . import stripe_payments
from .models import Order

STRIPE_KEYS = {
	'STRIPE_SECRET_KEY': 'sk_test_dummy',
	'STRIPE_WEBHOOK_SECRET': 'whsec_dummy',
}


def _fallback_rates():
	return core_views.FALLBACK_RATES, '', 'fallback'


def _session_event(order, *, event_type='checkout.session.completed', amount=None, status='paid'):
	return {
		'type': event_type,
		'data': {'object': {
			'id': 'cs_test_123',
			'client_reference_id': order.order_ref,
			'metadata': {'order_ref': order.order_ref},
			'payment_status': status,
			'amount_total': stripe_payments.to_minor_units(order.total_amount, order.currency) if amount is None else amount,
			'currency': order.currency.lower(),
		}},
	}


class MinorUnitTests(TestCase):
	def test_two_decimal_currency(self):
		self.assertEqual(stripe_payments.to_minor_units(Decimal('99.98'), 'USD'), 9998)

	def test_ugx_whole_shillings_sent_times_100(self):
		# Stripe: UGX is zero-decimal but sent as a two-decimal value ending in 00.
		# Sending 184963 would charge UGX 1,849.63 -> customer pays 1/100th of the order.
		self.assertEqual(stripe_payments.to_minor_units(Decimal('184963.40'), 'UGX'), 18496300)
		self.assertEqual(stripe_payments.to_minor_units(Decimal('184963.50'), 'UGX'), 18496400)
		self.assertEqual(stripe_payments.to_minor_units(Decimal('184963.50'), 'UGX') % 100, 0)


@patch('core.views._fetch_live_rates', _fallback_rates)
class CardCheckoutTests(TestCase):
	def setUp(self):
		category = Category.objects.create(name='Dresses', description='Dresses')
		self.product = Product.objects.create(
			name='Wrap Dress',
			description='Midi wrap dress',
			price_usd=Decimal('49.99'),
			price_ugx=Decimal('184963.00'),
			category=category,
			color='Red',
			sizes='36,38,40',
			stock_quantity=5,
			in_stock=True,
		)

	def _add_to_cart(self):
		self.client.post(reverse('add_to_cart', args=[self.product.id]), data={'quantity': 2, 'size': '38'})

	def test_card_not_offered_without_stripe_key(self):
		with override_settings(STRIPE_SECRET_KEY=''):
			self.assertNotIn('card', core_views._available_payment_methods())

	@override_settings(**STRIPE_KEYS)
	def test_card_checkout_redirects_to_stripe(self):
		self._add_to_cart()
		fake_stripe = MagicMock()
		fake_stripe.checkout.Session.create.return_value = MagicMock(url='https://checkout.stripe.test/s')
		with patch('cart.stripe_payments._stripe', return_value=fake_stripe):
			response = self.client.post(
				f"{reverse('checkout')}?payment_method=card",
				data={'name': 'Test Buyer', 'phone': '+256700000000', 'country': 'Uganda'},
			)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, 'https://checkout.stripe.test/s')
		order = Order.objects.get()
		self.assertEqual(order.payment_method, 'card')
		self.assertEqual(order.status, Order.STATUS_PENDING)
		params = fake_stripe.checkout.Session.create.call_args.kwargs
		self.assertEqual(params['mode'], 'payment')
		self.assertEqual(params['metadata'], {'order_ref': order.order_ref})
		self.assertEqual(params['line_items'][0]['price_data']['unit_amount'], 9998)
		self.assertIn('{CHECKOUT_SESSION_ID}', params['success_url'])

	@override_settings(**STRIPE_KEYS)
	def test_stripe_failure_keeps_order_and_shows_success_page(self):
		self._add_to_cart()
		fake_stripe = MagicMock()
		fake_stripe.checkout.Session.create.side_effect = RuntimeError('boom')
		with patch('cart.stripe_payments._stripe', return_value=fake_stripe):
			response = self.client.post(
				f"{reverse('checkout')}?payment_method=card",
				data={'name': 'Test Buyer', 'phone': '+256700000000', 'country': 'Uganda'},
			)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(Order.objects.get().status, Order.STATUS_PENDING)


@override_settings(**STRIPE_KEYS)
class StripeWebhookTests(TestCase):
	def setUp(self):
		self.order = Order.objects.create(
			customer_name='Test Buyer',
			phone='+256700000000',
			country='Uganda',
			payment_method='card',
			currency='USD',
			total_amount=Decimal('99.98'),
		)

	def _post(self, event):
		return self.client.post(
			reverse('stripe_webhook'),
			data=json.dumps(event),
			content_type='application/json',
			HTTP_STRIPE_SIGNATURE='t=1,v1=sig',
		)

	def test_rejects_bad_signature(self):
		fake_stripe = MagicMock()
		fake_stripe.Webhook.construct_event.side_effect = ValueError('bad signature')
		with patch('cart.stripe_payments._stripe', return_value=fake_stripe):
			response = self._post(_session_event(self.order))
		self.assertEqual(response.status_code, 400)
		self.order.refresh_from_db()
		self.assertEqual(self.order.status, Order.STATUS_PENDING)

	def test_completed_session_confirms_order(self):
		with patch('cart.stripe_payments._stripe', return_value=MagicMock()):
			response = self._post(_session_event(self.order))
		self.assertEqual(response.status_code, 200)
		self.order.refresh_from_db()
		self.assertEqual(self.order.status, Order.STATUS_CONFIRMED)
		self.assertIsNotNone(self.order.payment_confirmed_at)

	def test_amount_mismatch_leaves_order_pending(self):
		with patch('cart.stripe_payments._stripe', return_value=MagicMock()):
			self._post(_session_event(self.order, amount=100))
		self.order.refresh_from_db()
		self.assertEqual(self.order.status, Order.STATUS_PENDING)

	def test_unpaid_session_leaves_order_pending(self):
		with patch('cart.stripe_payments._stripe', return_value=MagicMock()):
			self._post(_session_event(self.order, status='unpaid'))
		self.order.refresh_from_db()
		self.assertEqual(self.order.status, Order.STATUS_PENDING)

	def test_does_not_rewind_shipped_order(self):
		self.order.status = Order.STATUS_SHIPPED
		self.order.save(update_fields=['status'])
		with patch('cart.stripe_payments._stripe', return_value=MagicMock()):
			self._post(_session_event(self.order))
		self.order.refresh_from_db()
		self.assertEqual(self.order.status, Order.STATUS_SHIPPED)

	def test_async_failure_marks_order_failed(self):
		with patch('cart.stripe_payments._stripe', return_value=MagicMock()):
			self._post(_session_event(self.order, event_type='checkout.session.async_payment_failed', status='unpaid'))
		self.order.refresh_from_db()
		self.assertEqual(self.order.status, Order.STATUS_FAILED)

	def test_success_page_confirms_from_session(self):
		session = _session_event(self.order)['data']['object']
		with patch('cart.stripe_payments.retrieve_session', return_value=session):
			response = self.client.get(f"{reverse('stripe_success')}?session_id=cs_test_123")
		self.assertEqual(response.status_code, 200)
		self.order.refresh_from_db()
		self.assertEqual(self.order.status, Order.STATUS_CONFIRMED)

	def test_cancel_page_keeps_order_pending(self):
		response = self.client.get(f"{reverse('stripe_cancel')}?order_ref={self.order.order_ref}")
		self.assertEqual(response.status_code, 200)
		self.order.refresh_from_db()
		self.assertEqual(self.order.status, Order.STATUS_PENDING)
