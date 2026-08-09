from django import forms

from finance.models import AccountPayable, AccountReceivable, Expense, ImportShipment


date_input = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
text_area = forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = [
            'category', 'sub_category', 'description', 'amount', 'currency',
            'payment_method', 'date', 'supplier_name', 'bill_number',
            'due_date', 'status', 'notes',
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'date': date_input,
            'due_date': date_input,
            'description': text_area,
            'notes': text_area,
            'sub_category': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'supplier_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bill_number': forms.TextInput(attrs={'class': 'form-control'}),
        }


class AccountPayableForm(forms.ModelForm):
    class Meta:
        model = AccountPayable
        fields = [
            'vendor_name', 'description', 'amount', 'amount_paid', 'currency',
            'bill_date', 'due_date', 'status', 'notes',
        ]
        widgets = {
            'vendor_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': text_area,
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'bill_date': date_input,
            'due_date': date_input,
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': text_area,
        }


class AccountReceivableForm(forms.ModelForm):
    class Meta:
        model = AccountReceivable
        fields = [
            'customer_name', 'customer_phone', 'description', 'amount', 'amount_paid',
            'currency', 'invoice_date', 'due_date', 'status', 'notes',
        ]
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'description': text_area,
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'invoice_date': date_input,
            'due_date': date_input,
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': text_area,
        }


class ImportShipmentForm(forms.ModelForm):
    class Meta:
        model = ImportShipment
        fields = [
            'vendor_name', 'source_country', 'order_date', 'expected_arrival',
            'status', 'total_value', 'shipping_cost', 'import_duty', 'notes',
        ]
        widgets = {
            'vendor_name': forms.TextInput(attrs={'class': 'form-control'}),
            'source_country': forms.TextInput(attrs={'class': 'form-control'}),
            'order_date': date_input,
            'expected_arrival': date_input,
            'status': forms.Select(attrs={'class': 'form-select'}),
            'total_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'shipping_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'import_duty': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': text_area,
        }
