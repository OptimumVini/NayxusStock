from django.shortcuts import render, redirect, get_object_or_404
from django.db import models, transaction
from django.db.models import Q, Sum, Count
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
import csv
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import CreateView, DetailView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Category, Product, StockMovement

# Create your views here.

@login_required
def category_list(request):
    """Liste des catégories avec recherche"""
    query = request.GET.get('search', '')
    categories = Category.objects.all()
    if query:
        categories = categories.filter(name__icontains=query)
    return render(request, 'inventory/category_list.html', {'categories': categories, 'search_query': query})

@login_required
def stock_movement_list(request):
    """Liste des mouvements de stock avec recherche"""
    query = request.GET.get('search', '')
    movements = StockMovement.objects.all().select_related('product', 'user').order_by('-date')
    if query:
        movements = movements.filter(Q(product__name__icontains=query) | Q(reason__icontains=query))
    return render(request, 'inventory/stock_movement_list.html', {'movements': movements[:50], 'search_query': query})

class ProductCreateView(PermissionRequiredMixin, CreateView):
    """Vue pour créer un nouveau produit"""
    permission_required = 'inventory.add_product'
    model = Product
    fields = ['name', 'category', 'description', 'purchase_price', 'selling_price', 'quantity', 'alert_threshold', 'image', 'barcode']
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('product_list')

    def form_valid(self, form):
        with transaction.atomic():
            initial_quantity = form.cleaned_data.get('quantity', 0)
            self.object = form.save()
            
            if initial_quantity > 0:
                # The save above already set the quantity.
                # StockMovement.save() will add it again, so we set it to 0 momentarily.
                qty_to_record = initial_quantity
                self.object.quantity = 0
                self.object.save()
                
                StockMovement.objects.create(
                    product=self.object,
                    movement_type=StockMovement.MovementType.ENTRY,
                    quantity=qty_to_record,
                    reason="Stock initial à la création",
                    user=self.request.user
                )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Ajouter un produit'
        return context

class ProductDetailView(LoginRequiredMixin, DetailView):
    """Vue pour voir les détails d'un produit"""
    model = Product
    template_name = 'inventory/product_detail.html'
    context_object_name = 'product'

class ProductUpdateView(PermissionRequiredMixin, UpdateView):
    """Vue pour modifier un produit"""
    permission_required = 'inventory.change_product'
    model = Product
    fields = ['name', 'category', 'description', 'purchase_price', 'selling_price', 'quantity', 'alert_threshold', 'image', 'barcode']
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('product_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Modifier le produit: {self.object.name}'
        return context

class CategoryDetailView(LoginRequiredMixin, DetailView):
    """Vue pour voir les détails d'une catégorie"""
    model = Category
    template_name = 'inventory/category_detail.html'
    context_object_name = 'category'

class CategoryUpdateView(PermissionRequiredMixin, UpdateView):
    """Vue pour modifier une catégorie"""
    permission_required = 'inventory.change_category'
    model = Category
    fields = ['name', 'parent', 'description']
    template_name = 'inventory/category_form.html'
    success_url = reverse_lazy('category_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Modifier la catégorie: {self.object.name}'
        return context

class CategoryDeleteView(PermissionRequiredMixin, DeleteView):
    """Vue pour supprimer une catégorie"""
    permission_required = 'inventory.delete_category'
    model = Category
    success_url = reverse_lazy('category_list')
    template_name = 'inventory/category_confirm_delete.html'

class StockMovementDetailView(LoginRequiredMixin, DetailView):
    """Vue pour voir les détails d'un mouvement de stock"""
    model = StockMovement
    template_name = 'inventory/stock_movement_detail.html'
    context_object_name = 'movement'


class CategoryCreateView(PermissionRequiredMixin, CreateView):
    """Vue pour créer une nouvelle catégorie"""
    permission_required = 'inventory.add_category'
    model = Category
    fields = ['name', 'parent', 'description']
    template_name = 'inventory/category_form.html'
    success_url = reverse_lazy('category_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Ajouter une catégorie'
        return context

class StockMovementCreateView(LoginRequiredMixin, CreateView):
    """Vue pour créer un nouveau mouvement de stock"""
    model = StockMovement
    fields = ['product', 'movement_type', 'quantity', 'reason']
    template_name = 'inventory/stock_movement_form.html'
    success_url = reverse_lazy('stock_movement_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nouveau mouvement de stock'
        return context

@login_required
def product_detail_json(request, pk):
    """Retourne les détails d'un produit en JSON pour les calculs en JS"""
    product = get_object_or_404(Product, pk=pk)
    return JsonResponse({
        'id': product.id,
        'name': product.name,
        'selling_price': float(product.selling_price),
        'quantity': product.quantity,
    })

@login_required
def export_products_csv(request):
    """Exporte la liste des produits en CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="produits.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Nom', 'Catégorie', 'Prix Achat', 'Prix Vente', 'Stock', 'Seuil Alerte'])
    
    products = Product.objects.all().select_related('category')
    for p in products:
        writer.writerow([p.name, p.category.name, p.purchase_price, p.selling_price, p.quantity, p.alert_threshold])
    
    return response

@login_required
def stock_entry_report(request):
    """Génère un rapport des entrées de stock sur une période donnée"""
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    movements = StockMovement.objects.filter(movement_type=StockMovement.MovementType.ENTRY).select_related('product', 'user').order_by('date')
    
    if start_date:
        movements = movements.filter(date__date__gte=start_date)
    if end_date:
        movements = movements.filter(date__date__lte=end_date)
    
    # Calcul des totaux
    total_qty = movements.aggregate(total=Sum('quantity'))['total'] or 0
    total_value = 0
    for mov in movements:
        total_value += mov.quantity * mov.product.purchase_price

    context = {
        'movements': movements,
        'start_date': start_date,
        'end_date': end_date,
        'total_qty': total_qty,
        'total_value': total_value,
        'today': timezone.now()
    }
    return render(request, 'inventory/stock_entry_report.html', context)

@login_required
@permission_required('inventory.add_product', raise_exception=True)
def inventory_report(request):
    """Génère un état de l'inventaire complet à l'instant T avec regroupement par catégorie"""
    products = Product.objects.all().select_related('category').order_by('category__name', 'name')
    
    # Regroupement par catégorie avec sous-totaux
    categories_list = Category.objects.filter(products__isnull=False).distinct().order_by('name')
    report_data = []
    
    for cat in categories_list:
        cat_products = products.filter(category=cat)
        cat_qty = 0
        cat_purchase_value = 0
        cat_selling_value = 0
        for p in cat_products:
            cat_qty += p.quantity
            cat_purchase_value += p.quantity * p.purchase_price
            cat_selling_value += p.quantity * p.selling_price
        
        report_data.append({
            'category': cat,
            'products': cat_products,
            'subtotal_qty': cat_qty,
            'subtotal_purchase_value': cat_purchase_value,
            'subtotal_selling_value': cat_selling_value,
        })

    # Calcul des totaux globaux
    summary = products.aggregate(
        total_items=Count('id'),
        total_qty=Sum('quantity'),
    )
    
    # Calcul manuel de la valeur totale pour éviter les erreurs d'agrégation d'expressions complexes selon les versions de DB
    total_purchase_value = 0
    total_selling_value = 0
    for p in products:
        total_purchase_value += p.quantity * p.purchase_price
        total_selling_value += p.quantity * p.selling_price

    context = {
        'report_data': report_data,
        'summary': {
            'total_items': summary['total_items'],
            'total_qty': summary['total_qty'],
            'total_purchase_value': total_purchase_value,
            'total_selling_value': total_selling_value,
        },
        'today': timezone.now()
    }
    return render(request, 'inventory/inventory_report.html', context)
