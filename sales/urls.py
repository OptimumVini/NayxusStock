from django.urls import path
from .views import (
    customer_list, invoice_list, sales_list, statistics,
    CustomerCreateView, InvoiceCreateView,
    CustomerDetailView, CustomerUpdateView,
    InvoiceDetailView, InvoiceUpdateView,
    download_invoice_pdf, export_invoices_csv, vendeur_bilan
)

urlpatterns = [
    # Clients
    path('clients/', customer_list, name='customer_list'),
    path('clients/add/', CustomerCreateView.as_view(), name='customer_add'),
    path('clients/<int:pk>/', CustomerDetailView.as_view(), name='customer_detail'),
    path('clients/<int:pk>/edit/', CustomerUpdateView.as_view(), name='customer_edit'),

    # Factures & Ventes
    path('factures/', invoice_list, name='invoice_list'),
    path('factures/add/', InvoiceCreateView.as_view(), name='invoice_add'),
    path('factures/<int:pk>/', InvoiceDetailView.as_view(), name='invoice_detail'),
    path('factures/<int:pk>/edit/', InvoiceUpdateView.as_view(), name='invoice_edit'),
    path('factures/<int:pk>/pdf/', download_invoice_pdf, name='invoice_pdf'),
    path('factures/bilan/', vendeur_bilan, name='vendeur_bilan'),
    path('factures/export/csv/', export_invoices_csv, name='export_invoices_csv'),
    path('ventes/', sales_list, name='sales_list'),
    
    # Stats
    path('statistiques/', statistics, name='statistics'),
]
