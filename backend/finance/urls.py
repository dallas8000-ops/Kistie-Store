from django.urls import path
from . import views

urlpatterns = [
    path('', views.finance_dashboard, name='finance_dashboard'),
    path('expenses/', views.expense_list, name='finance_expenses'),
    path('expenses/new/', views.expense_create, name='finance_expense_create'),
    path('expenses/<int:expense_id>/edit/', views.expense_edit, name='finance_expense_edit'),
    path('expenses/<int:expense_id>/delete/', views.expense_delete, name='finance_expense_delete'),
    path('payables/', views.payable_list, name='finance_payables'),
    path('payables/new/', views.payable_create, name='finance_payable_create'),
    path('payables/<int:payable_id>/edit/', views.payable_edit, name='finance_payable_edit'),
    path('payables/<int:payable_id>/delete/', views.payable_delete, name='finance_payable_delete'),
    path('receivables/', views.receivable_list, name='finance_receivables'),
    path('receivables/new/', views.receivable_create, name='finance_receivable_create'),
    path('receivables/<int:receivable_id>/edit/', views.receivable_edit, name='finance_receivable_edit'),
    path('receivables/<int:receivable_id>/delete/', views.receivable_delete, name='finance_receivable_delete'),
    path('shipments/', views.shipment_list, name='finance_shipments'),
    path('shipments/new/', views.shipment_create, name='finance_shipment_create'),
    path('shipments/<int:shipment_id>/edit/', views.shipment_edit, name='finance_shipment_edit'),
    path('shipments/<int:shipment_id>/delete/', views.shipment_delete, name='finance_shipment_delete'),
]
