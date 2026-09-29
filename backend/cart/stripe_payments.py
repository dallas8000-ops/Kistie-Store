"""Stripe Checkout (one-time card payment) for existing Orders.

Flow: checkout creates the Order as usual → we open a Checkout Session for its total →
Stripe calls /stripe/webhook with checkout.session.completed → the Order is marked
payment_confirmed. Card is only offered when STRIPE_SECRET_KEY is configured.
"""

import logging
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings

from .models import Order

logger = logging.getLogger(__name__)

# Zero-decimal for Stripe, but the API still expects a two-decimal value ending in 00
# (https://docs.stripe.com/currencies#special-cases): UGX 5 is sent as 500.
WHOLE_UNITS_X100_CURRENCIES = frozenset({'UGX'})


def stripe_enabled():
	return bool(getattr(settings, 'STRIPE_SECRET_KEY', ''))


def _stripe():
	import stripe

	stripe.api_key = settings.STRIPE_SECRET_KEY
	return stripe


def to_minor_units(amount, currency):
	amount = Decimal(amount)
	if currency.upper() in WHOLE_UNITS_X100_CURRENCIES:
		return int(amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)) * 100
	return int((amount * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def create_checkout_session(order, success_url, cancel_url):
	"""Open a one-time Checkout Session for the order total; returns the Stripe session."""
	params = {
		'mode': 'payment',
		'line_items': [{
			'quantity': 1,
			'price_data': {
				'currency': order.currency.lower(),
				'unit_amount': to_minor_units(order.total_amount, order.currency),
				'product_data': {'name': f'Kistie Store order {order.order_ref}'},
			},
		}],
		'client_reference_id': order.order_ref,
		'metadata': {'order_ref': order.order_ref},
		'success_url': success_url,
		'cancel_url': cancel_url,
	}
	if order.customer_email:
		params['customer_email'] = order.customer_email
	return _stripe().checkout.Session.create(**params)


def construct_event(payload, signature):
	"""Verify the Stripe-Signature header; raises ValueError / SignatureVerificationError."""
	secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
	if not secret:
		raise ValueError('STRIPE_WEBHOOK_SECRET is not configured')
	return _stripe().Webhook.construct_event(payload, signature, secret)


def as_dict(stripe_object):
	"""Plain dict from a StripeObject (API shape differs across stripe-python versions)."""
	for attr in ('to_dict_recursive', 'to_dict'):
		method = getattr(stripe_object, attr, None)
		if callable(method):
			return method()
	return dict(stripe_object)


def retrieve_session(session_id):
	return as_dict(_stripe().checkout.Session.retrieve(session_id))


def _order_for_session(session):
	metadata = session.get('metadata') or {}
	order_ref = metadata.get('order_ref') or session.get('client_reference_id')
	if not order_ref:
		return None
	return Order.objects.filter(order_ref=order_ref).first()


def confirm_paid_session(session):
	"""Mark the session's order paid if Stripe collected the full amount. Idempotent."""
	order = _order_for_session(session)
	if order is None:
		logger.warning('Stripe session %s has no matching order', session.get('id'))
		return None
	if session.get('payment_status') != 'paid':
		return order
	expected = to_minor_units(order.total_amount, order.currency)
	if session.get('amount_total') != expected or (session.get('currency') or '').upper() != order.currency.upper():
		logger.error(
			'Stripe amount mismatch for %s: got %s %s, expected %s %s',
			order.order_ref, session.get('amount_total'), session.get('currency'), expected, order.currency,
		)
		return order
	if order.status in (Order.STATUS_PENDING, Order.STATUS_FAILED):
		order.status = Order.STATUS_CONFIRMED
		order.save(update_fields=['status'])
	return order


def handle_event(event):
	event_type = event.get('type')
	session = (event.get('data') or {}).get('object') or {}
	if event_type in ('checkout.session.completed', 'checkout.session.async_payment_succeeded'):
		confirm_paid_session(session)
	elif event_type == 'checkout.session.async_payment_failed':
		order = _order_for_session(session)
		if order and order.status == Order.STATUS_PENDING:
			order.status = Order.STATUS_FAILED
			order.save(update_fields=['status'])
