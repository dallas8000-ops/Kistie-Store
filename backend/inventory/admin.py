

from decimal import Decimal, ROUND_HALF_UP

from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product, ProductImage, ProductReview, Shipment, Vendor
from .pricing import apply_price_suggestion, suggest_price_for_product


def _generated_catalog_description(product):
	name = (product.name or '').lower()

	color_keywords = {
		'black': 'black',
		'white': 'white',
		'ivory': 'ivory',
		'cream': 'cream',
		'navy': 'navy',
		'blue': 'blue',
		'teal': 'teal',
		'green': 'green',
		'emerald': 'emerald',
		'olive': 'olive',
		'purple': 'purple',
		'violet': 'violet',
		'lilac': 'lilac',
		'pink': 'pink',
		'blush': 'blush',
		'magenta': 'magenta',
		'fuchsia': 'fuchsia',
		'peach': 'peach',
		'yellow': 'yellow',
		'lemon': 'lemon',
		'mustard': 'mustard',
		'gold': 'gold',
		'orange': 'orange',
		'tan': 'tan',
		'camel': 'camel',
		'oatmeal': 'oatmeal',
		'grey': 'grey',
		'gray': 'gray',
		'burgundy': 'burgundy',
		'maroon': 'maroon',
		'red': 'red',
		'scarlet': 'scarlet',
		'rust': 'rust',
	}

	type_keywords = {
		'pantsuit': 'pantsuit',
		'suit': 'suit set',
		'blazer': 'blazer set',
		'waistcoat': 'waistcoat set',
		'dress': 'dress',
		'midi': 'midi dress',
		'mini': 'mini dress',
		'maxi': 'maxi dress',
		'gown': 'gown',
		'cocktail': 'cocktail look',
		'sheath': 'sheath silhouette',
		'wrap': 'wrap silhouette',
		'skirt': 'skirt set',
		'office': 'office-ready outfit',
	}

	vibe_phrases = [
		'made for polished daytime styling.',
		'ideal for elevated work-to-evening wear.',
		'crafted for confident, modern dressing.',
		'designed to stand out at special occasions.',
		'built for comfort with a refined finish.',
		'tailored for effortless, versatile outfits.',
	]

	color = ''
	for keyword, label in color_keywords.items():
		if keyword in name:
			color = label
			break

	item_type = 'fashion piece'
	for keyword, label in type_keywords.items():
		if keyword in name:
			item_type = label
			break

	key = f'{product.name}:{product.id}'
	vibe = vibe_phrases[sum(ord(char) for char in key) % len(vibe_phrases)]

	if color:
		return f'A {color} {item_type} {vibe}'
	return f'A {item_type} {vibe}'


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
	list_display = ('name', 'origin_country', 'contact_person', 'lead_time_days', 'created_at')
	list_filter = ('origin_country', 'created_at')
	search_fields = ('name', 'contact_person', 'email', 'whatsapp_number')
	ordering = ('name',)


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
	list_display = ('vendor', 'tracking_number', 'status', 'estimated_arrival', 'updated_at')
	list_filter = ('status', 'vendor', 'created_at')
	search_fields = ('tracking_number', 'notes', 'vendor__name')
	date_hierarchy = 'created_at'
	ordering = ('-created_at',)


class ProductImageInline(admin.TabularInline):
	model = ProductImage
	extra = 1


class ProductAdmin(admin.ModelAdmin):
	readonly_fields = ('in_stock', 'slug')
	list_display = (
		'name', 'slug', 'category', 'vendor', 'price_usd', 'stock_quantity', 'in_stock', 'created_at',
	)
	list_filter = ('category', 'vendor', 'in_stock', 'created_at')
	search_fields = ('name', 'slug', 'description', 'color', 'sizes', 'vendor_sku')
	list_editable = ('stock_quantity',)
	list_display_links = ('name',)
	date_hierarchy = 'created_at'
	ordering = ('-created_at',)
	autocomplete_fields = ('category', 'vendor')
	fieldsets = (
		('Product Information', {
			'fields': ('name', 'slug', 'category', 'vendor', 'description', 'color', 'stock_quantity', 'in_stock'),
			'description': 'Availability follows Stock quantity automatically (In stock is read-only).',
		}),
		('Pricing & Sourcing', {
			'fields': ('price_usd', 'price_ugx', 'old_price', 'sourcing_cost_usd', 'vendor_sku'),
			'description': 'Set prices in USD/UGX and track sourcing costs.'
		}),
		('Sizes', {
			'fields': ('sizes',)
		}),
	)
	inlines = [ProductImageInline]
	actions = [
		'generate_catalog_descriptions',
		'scan_and_apply_price_suggestions',
		'apply_discount_10',
		'apply_discount_20',
		'apply_discount_30',
		'clear_discount',
	]

	def save_model(self, request, obj, form, change):
		# Normalize EU sizes and derive in_stock (Product.clean) — admin sometimes skipped full_clean paths.
		obj.full_clean()
		super().save_model(request, obj, form, change)

	@admin.action(description='Generate catalog descriptions (for blank/auto-created only)')
	def generate_catalog_descriptions(self, request, queryset):
		updated = 0
		for product in queryset:
			description = (product.description or '').strip().lower()
			if description and description != 'auto-created from uploaded catalog image.':
				continue
			product.description = _generated_catalog_description(product)
			product.save(update_fields=['description'])
			updated += 1

		if updated == 0:
			self.message_user(request, 'No products were updated. Selected products already have custom descriptions.')
		else:
			self.message_user(request, f'Generated descriptions for {updated} product(s).')

	@admin.action(description='Scan web comparables and apply suggested prices')
	def scan_and_apply_price_suggestions(self, request, queryset):
		updated = 0
		skipped = 0

		for product in queryset.select_related('category'):
			suggestion = suggest_price_for_product(product)

			if suggestion.price_usd is None:
				skipped += 1
				continue

			if suggestion.confidence < 0.45:
				skipped += 1
				continue

			if apply_price_suggestion(product, suggestion):
				updated += 1

		if updated == 0:
			self.message_user(
				request,
				f'No prices updated. {skipped} product(s) skipped due to low confidence or missing comparable data.'
			)
		else:
			self.message_user(
				request,
				f'Updated prices for {updated} product(s). Skipped {skipped} product(s).'
			)

	def _apply_discount_percent(self, request, queryset, percent):
		multiplier = Decimal('1') - (Decimal(percent) / Decimal('100'))
		updated = 0
		skipped = 0

		for product in queryset:
			current_usd = Decimal(product.price_usd or 0)
			current_ugx = Decimal(product.price_ugx or 0)
			previous_usd = Decimal(product.old_price or 0)

			if current_usd <= 0 or current_ugx <= 0:
				skipped += 1
				continue

			if previous_usd > current_usd:
				base_usd = previous_usd
				if current_usd > 0:
					base_ugx = (current_ugx * (previous_usd / current_usd)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
				else:
					base_ugx = current_ugx
			else:
				base_usd = current_usd
				base_ugx = current_ugx

			new_usd = (base_usd * multiplier).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
			new_ugx = (base_ugx * multiplier).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

			if new_usd <= 0 or new_ugx <= 0:
				skipped += 1
				continue

			product.old_price = base_usd
			product.price_usd = new_usd
			product.price_ugx = new_ugx
			product.save(update_fields=['old_price', 'price_usd', 'price_ugx'])
			updated += 1

		self.message_user(
			request,
			f'Applied {percent}% discount to {updated} product(s). Skipped {skipped} product(s).'
		)

	@admin.action(description='Apply 10 percent discount')
	def apply_discount_10(self, request, queryset):
		self._apply_discount_percent(request, queryset, 10)

	@admin.action(description='Apply 20 percent discount')
	def apply_discount_20(self, request, queryset):
		self._apply_discount_percent(request, queryset, 20)

	@admin.action(description='Apply 30 percent discount')
	def apply_discount_30(self, request, queryset):
		self._apply_discount_percent(request, queryset, 30)

	@admin.action(description='Clear discount (restore original price)')
	def clear_discount(self, request, queryset):
		restored = 0
		skipped = 0

		for product in queryset:
			current_usd = Decimal(product.price_usd or 0)
			current_ugx = Decimal(product.price_ugx or 0)
			previous_usd = Decimal(product.old_price or 0)

			if previous_usd <= 0 or current_usd <= 0 or current_ugx <= 0:
				skipped += 1
				continue

			factor = (previous_usd / current_usd)
			restored_ugx = (current_ugx * factor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

			product.price_usd = previous_usd
			product.price_ugx = restored_ugx
			product.old_price = None
			product.save(update_fields=['price_usd', 'price_ugx', 'old_price'])
			restored += 1

		self.message_user(
			request,
			f'Cleared discount for {restored} product(s). Skipped {skipped} product(s).'
		)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
	list_display = ('name', 'product_count', 'id')
	search_fields = ('name', 'description')
	ordering = ('name',)

	@admin.display(description='Products')
	def product_count(self, obj):
		return obj.products.count()


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
	list_display = (
		'product', 'user', 'rating_stars', 'is_approved', 'title', 'created_at',
	)
	list_display_links = ('product', 'user')
	list_filter = ('is_approved', 'rating', 'created_at')
	search_fields = ('title', 'comment', 'product__name', 'user__username')
	list_editable = ('is_approved',)
	raw_id_fields = ('product', 'user')
	readonly_fields = ('created_at',)
	ordering = ('-created_at',)
	fieldsets = (
		(None, {
			'fields': ('product', 'user', 'rating', 'is_approved'),
		}),
		('Content', {
			'fields': ('title', 'comment'),
		}),
		('Meta', {
			'fields': ('created_at',),
		}),
	)

	list_display = (
		'product', 'user', 'rating_stars', 'sentiment_badge', 'is_approved', 'title', 'created_at',
	)

	@admin.display(description='Rating')
	def rating_stars(self, obj):
		return format_html('{} <span class="text-muted">/ 5</span>', obj.rating)

	@admin.display(description='Sentiment')
	def sentiment_badge(self, obj):
		colours = {'positive': '#198754', 'negative': '#dc3545', 'neutral': '#6c757d'}
		labels = {'positive': '😊 Positive', 'negative': '😞 Negative', 'neutral': '😐 Neutral'}
		if not obj.sentiment:
			return format_html('<span style="color:#aaa;">—</span>')
		colour = colours.get(obj.sentiment, '#6c757d')
		label = labels.get(obj.sentiment, obj.sentiment)
		return format_html(
			'<span style="color:{};font-weight:600;">{}</span>',
			colour, label,
		)


admin.site.register(Product, ProductAdmin)
