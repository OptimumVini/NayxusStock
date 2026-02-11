from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction, models
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.utils import timezone
import io
import csv
import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

from .models import Customer, Invoice, InvoiceItem
from .forms import InvoiceForm, InvoiceItemFormSet
from inventory.models import Product

# Create your views here.

@login_required
def customer_list(request):
    """Liste des clients avec recherche"""
    query = request.GET.get('search', '')
    customers = Customer.objects.all()
    if query:
        customers = customers.filter(Q(name__icontains=query) | Q(phone__icontains=query))
    return render(request, 'sales/customer_list.html', {'customers': customers, 'search_query': query})

@login_required
def invoice_list(request):
    """Liste des factures de l'utilisateur avec recherche et filtres"""
    # Filtre de base : seulement les factures de l'utilisateur connecté
    # Note: On laisse le staff voir toutes les factures si besoin, ou on restreint strictement?
    # Le prompt dit : "Chaque utilisateur connecté n'a accès qu'à ses ventes"
    invoices = Invoice.objects.filter(user=request.user).select_related('customer', 'user').order_by('-date')
    
    # Récupération des paramètres de filtrage
    query = request.GET.get('search', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    status = request.GET.get('status', '')

    # Recherche textuelle
    if query:
        invoices = invoices.filter(Q(number__icontains=query) | Q(customer__name__icontains=query))
    
    # Filtrage par date
    if start_date:
        invoices = invoices.filter(date__date__gte=start_date)
    if end_date:
        invoices = invoices.filter(date__date__lte=end_date)
    
    # Filtrage par statut
    if status and status != 'ALL':
        invoices = invoices.filter(status=status)

    # Calcul du récapitulatif pour les factures filtrées
    summary_data = invoices.aggregate(
        count=Count('id'),
        total=Sum('total_amount'),
        paid=Sum('paid_amount')
    )
    
    # Calcul du reste à payer global
    total_val = summary_data['total'] or 0
    paid_val = summary_data['paid'] or 0
    remaining_val = total_val - paid_val

    context = {
        'invoices': invoices,
        'search_query': query,
        'start_date': start_date,
        'end_date': end_date,
        'status_filter': status,
        'invoice_statuses': Invoice.Status.choices,
        'summary': {
            'count': summary_data['count'],
            'total': total_val,
            'paid': paid_val,
            'remaining': remaining_val
        }
    }
    return render(request, 'sales/invoice_list.html', context)

@login_required
def sales_list(request):
    """Liste des ventes (même que factures mais vue différente)"""
    return invoice_list(request) # On peut réutiliser la logique

@login_required
def statistics(request):
    """Page des statistiques avec graphiques"""
    # 6 derniers mois
    last_6_months = datetime.date.today() - datetime.timedelta(days=180)
    
    monthly_sales = Invoice.objects.filter(user=request.user, date__gte=last_6_months)\
        .annotate(month=TruncMonth('date'))\
        .values('month')\
        .annotate(total=Sum('total_amount'))\
        .order_by('month')

    # Préparation des données pour le graphe
    months = [item['month'].strftime('%b %Y') for item in monthly_sales]
    totals = [float(item['total']) for item in monthly_sales]

    context = {
        'total_products': Product.objects.count(),
        'total_customers': Customer.objects.count(),
        'total_invoices': Invoice.objects.filter(user=request.user).count(),
        'total_revenue': Invoice.objects.filter(user=request.user).aggregate(total=Sum('total_amount'))['total'] or 0,
        'months_json': months,
        'totals_json': totals,
    }
    return render(request, 'sales/statistics.html', context)

class CustomerDetailView(LoginRequiredMixin, DetailView):
    """Vue pour voir les détails d'un client"""
    model = Customer
    template_name = 'sales/customer_detail.html'
    context_object_name = 'customer'

class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    """Vue pour modifier un client"""
    model = Customer
    fields = ['name', 'email', 'phone', 'address']
    template_name = 'sales/customer_form.html'
    success_url = reverse_lazy('customer_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Modifier le client: {self.object.name}'
        return context

class InvoiceDetailView(LoginRequiredMixin, DetailView):
    """Vue pour voir les détails d'une facture"""
    model = Invoice
    template_name = 'sales/invoice_detail.html'
    context_object_name = 'invoice'

    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user)

class InvoiceUpdateView(LoginRequiredMixin, UpdateView):
    """Vue pour modifier une facture avec ses articles"""
    model = Invoice
    form_class = InvoiceForm
    template_name = 'sales/invoice_form.html'
    success_url = reverse_lazy('invoice_list')

    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Modifier la vente: {self.object.number}'
        if self.request.POST:
            context['items'] = InvoiceItemFormSet(self.request.POST, instance=self.object)
        else:
            context['items'] = InvoiceItemFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items = context['items']
        with transaction.atomic():
            self.object = form.save()
            if items.is_valid():
                items.instance = self.object
                items.save()
        return super().form_valid(form)

class CustomerCreateView(LoginRequiredMixin, CreateView):
    """Vue pour créer un nouveau client"""
    model = Customer
    fields = ['name', 'email', 'phone', 'address']
    template_name = 'sales/customer_form.html'
    success_url = reverse_lazy('customer_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Ajouter un client'
        return context

class InvoiceCreateView(LoginRequiredMixin, CreateView):
    """Vue pour créer une nouvelle facture avec ses articles"""
    model = Invoice
    form_class = InvoiceForm
    template_name = 'sales/invoice_form.html'
    success_url = reverse_lazy('invoice_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nouvelle vente'
        if self.request.POST:
            context['items'] = InvoiceItemFormSet(self.request.POST)
        else:
            context['items'] = InvoiceItemFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items = context['items']
        with transaction.atomic():
            form.instance.user = self.request.user
            self.object = form.save()
            if items.is_valid():
                items.instance = self.object
                items.save()
            else:
                return self.render_to_response(self.get_context_data(form=form))
        return super().form_valid(form)

@login_required
def download_invoice_pdf(request, pk):
    """Génère et télécharge la facture au format PDF (sécurisé)"""
    invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
    
    # Création du buffer pour le PDF
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    from core.models import StoreSettings
    store = StoreSettings.get_settings()

    # En-tête
    y = height - 50
    
    # Infos Facture (à droite)
    p.setFont("Helvetica-Bold", 14)
    p.drawRightString(width - 50, height - 50, f"FACTURE #{invoice.number}")
    p.setFont("Helvetica", 10)
    p.drawRightString(width - 50, height - 70, f"Date: {invoice.date.strftime('%d/%m/%Y %H:%M')}")
    p.drawRightString(width - 50, height - 85, f"Vendeur: {invoice.user.username}")

    # Logo et Infos Boutique (à gauche)
    if store.logo:
        try:
            p.drawImage(store.logo.path, 50, height - 85, height=50, preserveAspectRatio=True, mask='auto')
            y = height - 105
        except Exception:
            y = height - 50
    
    p.setFont("Helvetica-Bold", 20)
    p.drawString(50, y, store.name)
    y -= 25
    
    p.setFont("Helvetica", 10)
    p.drawString(50, y, store.address or "Solutions de Gestion de Stock")
    y -= 30

    # Ligne de séparation
    p.line(50, y, width - 50, y)
    y -= 25

    # Infos Client
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Facturé à :")
    y -= 20
    p.setFont("Helvetica", 11)
    p.drawString(50, y, invoice.customer.name)
    if invoice.customer.address:
        y -= 15
        p.drawString(50, y, invoice.customer.address)
    if invoice.customer.phone:
        y -= 15
        p.drawString(50, y, f"Tél: {invoice.customer.phone}")

    # Tableau des articles
    data = [['Désignation', 'Prix Unit.', 'Qté', 'Sous-total']]
    for item in invoice.items.all():
        data.append([
            item.product.name,
            f"{item.unit_price} FCFA",
            str(item.quantity),
            f"{item.subtotal} FCFA"
        ])
    
    table = Table(data, colWidths=[250, 100, 50, 100])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    table.setStyle(style)
    
    # Positionnement du tableau
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, height - 250 - (len(data) * 20))

    # Totaux
    y_pos = height - 280 - (len(data) * 20)
    p.setFont("Helvetica-Bold", 12)
    p.drawRightString(width - 50, y_pos, f"TOTAL: {invoice.total_amount} FCFA")
    p.setFont("Helvetica", 11)
    p.drawRightString(width - 50, y_pos - 20, f"Payé: {invoice.paid_amount} FCFA")
    
    p.setFont("Helvetica-Bold", 14)
    p.setFillColor(colors.red if invoice.remaining_amount > 0 else colors.green)
    p.drawRightString(width - 50, y_pos - 45, f"Reste à Payer: {invoice.remaining_amount} FCFA")

    # Finalisation
    p.showPage()
    p.save()

    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf', 
                        headers={'Content-Disposition': f'attachment; filename="facture_{invoice.number}.pdf"'})

@login_required
def export_invoices_csv(request):
    """Exporte la liste des factures en CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="factures.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Numéro', 'Date', 'Client', 'Statut', 'Total', 'Payé', 'Reste'])
    
    invoices = Invoice.objects.filter(user=request.user).select_related('customer')
    for inv in invoices:
        writer.writerow([
            inv.number, 
            inv.date.strftime('%Y-%m-%d'), 
            inv.customer.name, 
            inv.get_status_display(), 
            inv.total_amount, 
            inv.paid_amount, 
            inv.remaining_amount
        ])
    
    return response

@login_required
def vendeur_bilan(request):
    """Génère une vue de bilan de vente pour l'utilisateur connecté"""
    # Filtre de base : seulement les factures de l'utilisateur connecté
    invoices = Invoice.objects.filter(user=request.user).select_related('customer').order_by('date')
    
    # Récupération des paramètres de filtrage
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    status = request.GET.get('status', '')

    # Filtrage par date
    if start_date:
        invoices = invoices.filter(date__date__gte=start_date)
    if end_date:
        invoices = invoices.filter(date__date__lte=end_date)
    
    # Filtrage par statut
    if status and status != 'ALL':
        invoices = invoices.filter(status=status)

    # Calcul du récapitulatif
    summary = invoices.aggregate(
        count=Count('id'),
        total=Sum('total_amount'),
        paid=Sum('paid_amount')
    )
    
    total_val = summary['total'] or 0
    paid_val = summary['paid'] or 0
    remaining_val = total_val - paid_val

    context = {
        'invoices': invoices,
        'start_date': start_date,
        'end_date': end_date,
        'summary': {
            'count': summary['count'],
            'total': total_val,
            'paid': paid_val,
            'remaining': remaining_val
        },
        'today': timezone.now()
    }
    return render(request, 'sales/vendeur_bilan.html', context)
