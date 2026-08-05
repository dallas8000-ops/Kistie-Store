
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


EU_SIZE_RANGE = tuple(str(size) for size in range(32, 56, 2))
EU_SIZE_SET = set(EU_SIZE_RANGE)


def _normalize_size_token(value):
	cleaned = value.strip().upper()
	if cleaned.startswith('EU '):
		cleaned = cleaned[3:].strip()
	if cleaned not in EU_SIZE_SET:
		raise ValidationError(f'Use EU sizes only. Allowed sizes: {", ".join(EU_SIZE_RANGE)}.')
	return cleaned


def normalize_eu_sizes(value):
	if not value:
		return []

	normalized = []
	for token in value.split(','):
		if not token.strip():
			continue
		size = _normalize_size_token(token)
		if size not in normalized:
			normalized.append(size)

	return sorted(normalized, key=lambda size: EU_SIZE_RANGE.index(size))


def validate_eu_sizes(value):
	normalize_eu_sizes(value)


def unique_product_slug(name, exclude_pk=None):
	"""Stable URL slug from product name; append -2, -3, … on collision."""
	base = slugify(name)[:200] or 'product'
	slug = base
	counter = 2
	qs = Product.objects.all()
	if exclude_pk is not None:
		qs = qs.exclude(pk=exclude_pk)
	while qs.filter(slug=slug).exists():
		suffix = f'-{counter}'
		slug = f'{base[: 200 - len(suffix)]}{suffix}'
		counter += 1
	return slug


class Category(models.Model):
	name = models.CharField(max_length=100)
	description = models.TextField(blank=True)

	class Meta:
		verbose_name_plural = 'Categories'

	def __str__(self):
		return self.name


class Vendor(models.Model):
	name = models.CharField(max_length=200)
	origin_country = models.CharField(max_length=100, help_text='e.g., Turkey, China, UK')
	contact_person = models.CharField(max_length=200, blank=True)
	email = models.EmailField(blank=True)
	whatsapp_number = models.CharField(max_length=20, blank=True)
	lead_time_days = models.PositiveIntegerField(default=14)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.name} ({self.origin_country})"


class Product(models.Model):
	name = models.CharField(max_length=200)
	slug = models.SlugField(max_length=220, unique=True, blank=True)
	description = models.TextField(blank=True)
	price_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Price in USD')
	price_ugx = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Price in UGX (Ugandan Shilling)')
	old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
	vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
	sourcing_cost_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	vendor_sku = models.CharField(max_length=100, blank=True)
	color = models.CharField(max_length=100, blank=True)
	stock_quantity = models.PositiveIntegerField(default=1, help_text='Number of units currently available for sale')
	sizes = models.CharField(
		max_length=200,
		help_text='Comma-separated EU sizes, e.g. 32,34,36,38,40,42,44,46,48,50,52,54',
		blank=True,
		validators=[validate_eu_sizes],
	)
	in_stock = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	@property
	def price(self):
		"""For backward compatibility, returns USD price"""
		return self.price_usd

	def size_list(self):
		return normalize_eu_sizes(self.sizes)

	def clean(self):
		super().clean()
		if self.sizes:
			self.sizes = ','.join(normalize_eu_sizes(self.sizes))

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = unique_product_slug(self.name, exclude_pk=self.pk)
		# Always derive availability from quantity (single source of truth).
		self.in_stock = self.stock_quantity > 0
		# Admin/list saves often use save(update_fields=['stock_quantity']) — without merging,
		# "in_stock" would never be written and the storefront still sees out-of-stock.
		update_fields = kwargs.get('update_fields')
		if update_fields is not None:
			merged = tuple(dict.fromkeys(tuple(update_fields) + ('in_stock',)))
			if not self.slug and 'slug' not in merged:
				merged = tuple(dict.fromkeys(merged + ('slug',)))
			kwargs['update_fields'] = merged
		super().save(*args, **kwargs)

	def get_absolute_url(self):
		return reverse('product_detail', args=[self.slug])

	def __str__(self):
		return self.name


class ProductImage(models.Model):
	product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
	image = models.ImageField(upload_to='products/')
	alt_text = models.CharField(max_length=255, blank=True)

	def __str__(self):
		return f"Image for {self.product.name}"


class ProductReview(models.Model):
	"""Approved reviews surface on the catalog; staff moderate via Django admin."""

	product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='product_reviews',
	)
	rating = models.PositiveSmallIntegerField(
		validators=[MinValueValidator(1), MaxValueValidator(5)],
		help_text='1–5 stars',
	)
	title = models.CharField(max_length=120, blank=True)
	comment = models.TextField(blank=True)
	SENTIMENT_CHOICES = [
		('positive', 'Positive'),
		('negative', 'Negative'),
		('neutral', 'Neutral'),
	]

	is_approved = models.BooleanField(
		default=False,
		help_text='Only approved reviews count toward catalog averages.',
	)
	sentiment = models.CharField(
		max_length=10,
		blank=True,
		choices=SENTIMENT_CHOICES,
		help_text='Auto-detected by AI when the review is approved.',
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']
		constraints = [
			models.UniqueConstraint(
				fields=('product', 'user'),
				name='inventory_productreview_unique_per_user',
			),
		]
		verbose_name = 'Product review'
		verbose_name_plural = 'Product reviews'

	def __str__(self):
		return f'{self.rating}★ — {self.product.name} ({self.user})'


class Shipment(models.Model):
	STATUS_CHOICES = [
		('ordered', 'Ordered'),
		('in_transit', 'In Transit'),
		('at_customs', 'At Customs'),
		('received', 'Received in Kampala'),
	]

	vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
	tracking_number = models.CharField(max_length=100, blank=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ordered')
	estimated_arrival = models.DateField(null=True, blank=True)
	notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"Shipment from {self.vendor.name} - {self.status}"
