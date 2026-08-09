from django.contrib import admin
from .models import Expense, AccountReceivable, AccountPayable, ImportShipment


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('date', 'category', 'amount', 'currency', 'payment_method', 'status', 'supplier_name')
    list_filter = ('category', 'payment_method', 'status', 'currency')
    search_fields = ('description', 'supplier_name', 'bill_number')


@admin.register(AccountReceivable)
class AccountReceivableAdmin(admin.ModelAdmin):
    list_display = ('invoice_date', 'customer_name', 'amount', 'amount_paid', 'balance_due', 'status', 'due_date')
    list_filter = ('status', 'currency')
    search_fields = ('customer_name', 'description')


@admin.register(AccountPayable)
class AccountPayableAdmin(admin.ModelAdmin):
    list_display = ('bill_date', 'vendor_name', 'amount', 'amount_paid', 'balance_due', 'status', 'due_date')
    list_filter = ('status', 'currency')
    search_fields = ('vendor_name', 'description')


@admin.register(ImportShipment)
class ImportShipmentAdmin(admin.ModelAdmin):
    list_display = ('order_date', 'source_country', 'status', 'total_value', 'shipping_cost', 'import_duty')
    list_filter = ('status', 'source_country')
    search_fields = ('vendor_name', 'notes')
