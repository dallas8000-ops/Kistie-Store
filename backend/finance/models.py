from decimal import Decimal
from django.db import models
from django.utils import timezone


class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('household', 'Household'),
        ('business_operational', 'Business operations'),
        ('business_rent', 'Rent / utilities'),
        ('business_staff', 'Staff'),
        ('business_marketing', 'Marketing'),
        ('other', 'Other'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile money'),
        ('bank_transfer', 'Bank transfer'),
        ('credit', 'Credit'),
    ]
    STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('open', 'Open'),
        ('partial', 'Partial'),
        ('overdue', 'Overdue'),
    ]

    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default='other')
    sub_category = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    payment_method = models.CharField(max_length=32, choices=PAYMENT_METHOD_CHOICES, default='cash')
    date = models.DateField(default=timezone.now)
    supplier_name = models.CharField(max_length=200, blank=True)
    bill_number = models.CharField(max_length=120, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='paid')
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Expense'
        verbose_name_plural = 'Expenses'

    def __str__(self):
        return f"{self.category} expense on {self.date} — {self.amount} {self.currency}"


class AccountReceivable(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
        ('void', 'Void'),
    ]

    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=40, blank=True)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=10, default='USD')
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-invoice_date']
        verbose_name = 'Account receivable'
        verbose_name_plural = 'Accounts receivable'

    def __str__(self):
        return f"{self.customer_name} — {self.amount} {self.currency}"

    @property
    def balance_due(self) -> Decimal:
        return max(self.amount - self.amount_paid, Decimal('0.00'))


class AccountPayable(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
        ('void', 'Void'),
    ]

    vendor_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=10, default='USD')
    bill_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-bill_date']
        verbose_name = 'Account payable'
        verbose_name_plural = 'Accounts payable'

    def __str__(self):
        return f"{self.vendor_name} — {self.amount} {self.currency}"

    @property
    def balance_due(self) -> Decimal:
        return max(self.amount - self.amount_paid, Decimal('0.00'))


class ImportShipment(models.Model):
    STATUS_CHOICES = [
        ('ordered', 'Ordered'),
        ('in_transit', 'In transit'),
        ('received', 'Received'),
        ('stored', 'In store'),
    ]

    vendor_name = models.CharField(max_length=200, blank=True)
    source_country = models.CharField(max_length=100, blank=True)
    order_date = models.DateField(default=timezone.now)
    expected_arrival = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='ordered')
    total_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    import_duty = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-order_date']
        verbose_name = 'Import shipment'
        verbose_name_plural = 'Import shipments'

    def __str__(self):
        return f"Shipment from {self.source_country or 'unknown'} on {self.order_date}"

    @property
    def total_landed_cost(self) -> Decimal:
        return self.total_value + self.shipping_cost + self.import_duty
