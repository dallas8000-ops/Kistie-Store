from django.contrib import admin

from .models import Cart, CartItem, Order, OrderItem

class CartItemInline(admin.TabularInline):
	model = CartItem
	extra = 1

class CartAdmin(admin.ModelAdmin):
	inlines = [CartItemInline]
	list_display = ('id', 'user', 'session_key', 'item_count', 'created_at')
	list_filter = ('created_at',)
	search_fields = ('session_key', 'user__username', 'user__email')
	ordering = ('-created_at',)

	@admin.display(description='Items')
	def item_count(self, obj):
		return obj.items.count()


class OrderItemInline(admin.TabularInline):
	model = OrderItem
	extra = 0
	readonly_fields = ('product_name', 'quantity', 'size', 'color', 'unit_price', 'line_total')
	can_delete = False


class OrderAdmin(admin.ModelAdmin):
	list_display = (
		'order_ref', 'customer_name', 'phone', 'country', 'payment_method',
		'currency', 'total_amount', 'status', 'created_at',
	)
	list_filter = ('status', 'payment_method', 'currency', 'created_at')
	search_fields = ('order_ref', 'customer_name', 'phone')
	readonly_fields = (
		'order_ref', 'created_at', 'payment_confirmed_at', 'packed_at', 'shipped_at', 'delivered_at',
	)
	list_editable = ('status',)
	fieldsets = (
		(None, {
			'fields': (
				'order_ref', 'status', 'user', 'session_key',
				'customer_name', 'customer_email', 'phone', 'country', 'notes',
			),
		}),
		('Payment', {
			'fields': ('payment_method', 'currency', 'total_amount'),
		}),
		('Fulfillment', {
			'fields': ('tracking_url', 'payment_confirmed_at', 'packed_at', 'shipped_at', 'delivered_at'),
			'description': 'Set status to Packed / Shipped / Delivered as the order progresses. Timestamps fill automatically.',
		}),
		('Meta', {'fields': ('created_at',)}),
	)
	inlines = [OrderItemInline]


admin.site.register(Cart, CartAdmin)
admin.site.register(Order, OrderAdmin)
