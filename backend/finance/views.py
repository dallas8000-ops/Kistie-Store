from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from finance.forms import AccountPayableForm, AccountReceivableForm, ExpenseForm, ImportShipmentForm
from finance.models import AccountPayable, AccountReceivable, Expense, ImportShipment


DELETE_CONFIRM_TEMPLATE = 'finance/delete_confirm.html'


@require_GET
@permission_required('core.access_staff_dashboard', raise_exception=True)
def finance_dashboard(request):
    finance_total_expenses = Expense.objects.aggregate(total=Sum('amount'))['total'] or 0
    finance_open_payables = AccountPayable.objects.filter(status__in=['open', 'partial']).aggregate(
        total=Sum(ExpressionWrapper(F('amount') - F('amount_paid'), output_field=DecimalField())),
    )['total'] or 0
    finance_open_receivables = AccountReceivable.objects.filter(status__in=['open', 'partial']).aggregate(
        total=Sum(ExpressionWrapper(F('amount') - F('amount_paid'), output_field=DecimalField())),
    )['total'] or 0
    open_payables = AccountPayable.objects.filter(status__in=['open', 'partial']).order_by('due_date')[:20]
    open_receivables = AccountReceivable.objects.filter(status__in=['open', 'partial']).order_by('due_date')[:20]
    inbound_shipments = ImportShipment.objects.filter(status__in=['ordered', 'in_transit']).order_by('order_date')[:20]
    expense_breakdown = (
        Expense.objects
        .values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')[:8]
    )

    return render(request, 'finance/dashboard.html', {
        'finance_total_expenses': finance_total_expenses,
        'finance_open_payables': finance_open_payables,
        'finance_open_receivables': finance_open_receivables,
        'open_payables': open_payables,
        'open_receivables': open_receivables,
        'inbound_shipments': inbound_shipments,
        'expense_breakdown': expense_breakdown,
        'expense_count': Expense.objects.count(),
        'payable_count': AccountPayable.objects.count(),
        'receivable_count': AccountReceivable.objects.count(),
        'shipment_count': ImportShipment.objects.count(),
    })


@require_GET
@permission_required('core.access_staff_dashboard', raise_exception=True)
def expense_list(request):
    expenses = Expense.objects.order_by('-date')[:100]
    return render(request, 'finance/expense_list.html', {'expenses': expenses})


@require_http_methods(['GET', 'POST'])
@permission_required('core.access_staff_dashboard', raise_exception=True)
def expense_create(request):
    form = ExpenseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Expense saved successfully.')
        return redirect('finance_expenses')
    return render(request, 'finance/expense_form.html', {'form': form})


@require_http_methods(['GET', 'POST'])
@permission_required('core.access_staff_dashboard', raise_exception=True)
def expense_edit(request, expense_id):
    expense = get_object_or_404(Expense, pk=expense_id)
    form = ExpenseForm(request.POST or None, instance=expense)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Expense updated successfully.')
        return redirect('finance_expenses')
    return render(request, 'finance/expense_form.html', {'form': form, 'record': expense})


@require_http_methods(['GET', 'POST'])
@permission_required('core.access_staff_dashboard', raise_exception=True)
def expense_delete(request, expense_id):
    expense = get_object_or_404(Expense, pk=expense_id)
    if request.method == 'POST':
        expense.delete()
        messages.success(request, 'Expense deleted successfully.')
        return redirect('finance_expenses')
    return render(request, DELETE_CONFIRM_TEMPLATE, {
        'record_name': str(expense),
        'cancel_url_name': 'finance_expenses',
    })


@require_GET
@permission_required('core.access_staff_dashboard', raise_exception=True)
def payable_list(request):
    payables = AccountPayable.objects.order_by('due_date')[:100]
    return render(request, 'finance/payable_list.html', {'payables': payables})


@require_http_methods(['GET', 'POST'])
@permission_required('core.access_staff_dashboard', raise_exception=True)
def payable_create(request):
    form = AccountPayableForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Payable saved successfully.')
        return redirect('finance_payables')
    return render(request, 'finance/payable_form.html', {'form': form})


@require_http_methods(['GET', 'POST'])
@permission_required('core.access_staff_dashboard', raise_exception=True)
def payable_edit(request, payable_id):
    payable = get_object_or_404(AccountPayable, pk=payable_id)
    form = AccountPayableForm(request.POST or None, instance=payable)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Payable updated successfully.')
        return redirect('finance_payables')
    return render(request, 'finance/payable_form.html', {'form': form, 'record': payable})


@require_http_methods(['GET', 'POST'])
@permission_required('core.access_staff_dashboard', raise_exception=True)
def payable_delete(request, payable_id):
    payable = get_object_or_404(AccountPayable, pk=payable_id)
    if request.method == 'POST':
        payable.delete()
        messages.success(request, 'Payable deleted successfully.')
        return redirect('finance_payables')
    return render(request, DELETE_CONFIRM_TEMPLATE, {
        'record_name': str(payable),
        'cancel_url_name': 'finance_payables',
    })


@require_GET
@permission_required('core.access_staff_dashboard', raise_exception=True)
def receivable_list(request):
    receivables = AccountReceivable.objects.order_by('due_date')[:100]
    return render(request, 'finance/receivable_list.html', {'receivables': receivables})


@require_http_methods(['GET', 'POST'])
@permission_required('core.access_staff_dashboard', raise_exception=True)
def receivable_create(request):
    form = AccountReceivableForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Receivable saved successfully.')
        return redirect('finance_receivables')
    return render(request, 'finance/receivable_form.html', {'form': form})


@require_http_methods(['GET', 'POST'])
@permission_required('core.access_staff_dashboard', raise_exception=True)
def receivable_edit(request, receivable_id):
    receivable = get_object_or_404(AccountReceivable, pk=receivable_id)
    form = AccountReceivableForm(request.POST or None, instance=receivable)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Receivable updated successfully.')
        return redirect('finance_receivables')
    return render(request, 'finance/receivable_form.html', {'form': form, 'record': receivable})


@require_http_methods(['GET', 'POST'])
@permission_required('core.access_staff_dashboard', raise_exception=True)
def receivable_delete(request, receivable_id):
    receivable = get_object_or_404(AccountReceivable, pk=receivable_id)
    if request.method == 'POST':
        receivable.delete()
        messages.success(request, 'Receivable deleted successfully.')
        return redirect('finance_receivables')
    return render(request, DELETE_CONFIRM_TEMPLATE, {
        'record_name': str(receivable),
        'cancel_url_name': 'finance_receivables',
    })


@require_GET
@permission_required('core.access_staff_dashboard', raise_exception=True)
def shipment_list(request):
    shipments = ImportShipment.objects.order_by('-order_date')[:100]
    return render(request, 'finance/shipment_list.html', {'shipments': shipments})


@require_http_methods(['GET', 'POST'])
@permission_required('core.access_staff_dashboard', raise_exception=True)
def shipment_create(request):
    form = ImportShipmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Shipment saved successfully.')
        return redirect('finance_shipments')
    return render(request, 'finance/shipment_form.html', {'form': form})


@require_http_methods(['GET', 'POST'])
@permission_required('core.access_staff_dashboard', raise_exception=True)
def shipment_edit(request, shipment_id):
    shipment = get_object_or_404(ImportShipment, pk=shipment_id)
    form = ImportShipmentForm(request.POST or None, instance=shipment)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Shipment updated successfully.')
        return redirect('finance_shipments')
    return render(request, 'finance/shipment_form.html', {'form': form, 'record': shipment})


@require_http_methods(['GET', 'POST'])
@permission_required('core.access_staff_dashboard', raise_exception=True)
def shipment_delete(request, shipment_id):
    shipment = get_object_or_404(ImportShipment, pk=shipment_id)
    if request.method == 'POST':
        shipment.delete()
        messages.success(request, 'Shipment deleted successfully.')
        return redirect('finance_shipments')
    return render(request, DELETE_CONFIRM_TEMPLATE, {
        'record_name': str(shipment),
        'cancel_url_name': 'finance_shipments',
    })
