
from django.db import models
from django.conf import settings
from django.utils import timezone
from inventory.models import Product
from uuid import uuid4

class Cart(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
	session_key = models.CharField(max_length=40, null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"Cart {self.id}"


class CartItem(models.Model):
	cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey(Product, on_delete=models.CASCADE)
	quantity = models.PositiveIntegerField(default=1)
	size = models.CharField(max_length=50, blank=True)
	color = models.CharField(max_length=50, blank=True)

	def __str__(self):
		return f"{self.quantity} x {self.product.name} ({self.size}, {self.color})"


class Order(models.Model):
	STATUS_PENDING = 'pending_payment'
	STATUS_CONFIRMED = 'payment_confirmed'
	STATUS_PACKED = 'packed'
	STATUS_SHIPPED = 'shipped'
	STATUS_DELIVERED = 'delivered'
	STATUS_FAILED = 'payment_failed'
	STATUS_CHOICES = (
		(STATUS_PENDING, 'Placed — pending payment'),
		(STATUS_CONFIRMED, 'Payment received'),
		(STATUS_PACKED, 'Packed'),
		(STATUS_SHIPPED, 'Shipped'),
		(STATUS_DELIVERED, 'Delivered'),
		(STATUS_FAILED, 'Payment failed'),
	)

	PROGRESS_STATUSES = (
		STATUS_PENDING,
		STATUS_CONFIRMED,
		STATUS_PACKED,
		STATUS_SHIPPED,
		STATUS_DELIVERED,
	)

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
	session_key = models.CharField(max_length=40, null=True, blank=True)
	order_ref = models.CharField(max_length=20, unique=True, editable=False)
	customer_name = models.CharField(max_length=120)
	customer_email = models.EmailField(
		max_length=254,
		blank=True,
		help_text='Optional — used for order status updates.',
	)
	phone = models.CharField(max_length=30)
	country = models.CharField(max_length=60)
	notes = models.TextField(blank=True)
	payment_method = models.CharField(max_length=20)
	currency = models.CharField(max_length=10, default='USD')
	total_amount = models.DecimalField(max_digits=12, decimal_places=2)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
	tracking_url = models.URLField(max_length=500, blank=True, help_text='Courier tracking link (shown when shipped).')
	payment_confirmed_at = models.DateTimeField(null=True, blank=True)
	packed_at = models.DateTimeField(null=True, blank=True)
	shipped_at = models.DateTimeField(null=True, blank=True)
	delivered_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def save(self, *args, **kwargs):
		if not self.order_ref:
			self.order_ref = f"KS-{uuid4().hex[:8].upper()}"

		if self.pk:
			previous_status = (
				Order.objects.filter(pk=self.pk).values_list('status', flat=True).first()
			)
			if previous_status and previous_status != self.status:
				now = timezone.now()
				if self.status == self.STATUS_CONFIRMED and not self.payment_confirmed_at:
					self.payment_confirmed_at = now
				elif self.status == self.STATUS_PACKED and not self.packed_at:
					self.packed_at = now
				elif self.status == self.STATUS_SHIPPED and not self.shipped_at:
					self.shipped_at = now
				elif self.status == self.STATUS_DELIVERED and not self.delivered_at:
					self.delivered_at = now
				# Backfill earlier milestones when staff jump ahead.
				if self.status in (self.STATUS_PACKED, self.STATUS_SHIPPED, self.STATUS_DELIVERED):
					if not self.payment_confirmed_at:
						self.payment_confirmed_at = now
				if self.status in (self.STATUS_SHIPPED, self.STATUS_DELIVERED):
					if not self.packed_at:
						self.packed_at = now
				if self.status == self.STATUS_DELIVERED and not self.shipped_at:
					self.shipped_at = now

		update_fields = kwargs.get('update_fields')
		if update_fields is not None:
			extra = (
				'payment_confirmed_at', 'packed_at', 'shipped_at', 'delivered_at',
			)
			kwargs['update_fields'] = tuple(dict.fromkeys(tuple(update_fields) + extra))

		super().save(*args, **kwargs)

	def __str__(self):
		return f"{self.order_ref} - {self.customer_name}"


class OrderItem(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
	product_name = models.CharField(max_length=200)
	quantity = models.PositiveIntegerField(default=1)
	size = models.CharField(max_length=50, blank=True)
	color = models.CharField(max_length=50, blank=True)
	unit_price = models.DecimalField(max_digits=12, decimal_places=2)
	line_total = models.DecimalField(max_digits=12, decimal_places=2)

	def __str__(self):
		return f"{self.quantity} x {self.product_name}"
