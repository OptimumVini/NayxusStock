from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import StoreSettings
from inventory.models import Product, Category, StockMovement
from sales.models import Invoice, Customer

class StoreSettingsUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Vue pour modifier les informations du magasin"""
    model = StoreSettings
    fields = ['name', 'address', 'phone', 'email', 'logo']
    template_name = 'core/store_settings_form.html'
    success_url = reverse_lazy('dashboard')

    def get_object(self, queryset=None):
        return StoreSettings.get_settings()

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Paramètres du Magasin'
        return context

@login_required(login_url='login')
def product_list(request):
    """
    Vue de la liste des produits avec recherche, filtre et modes d'affichage.
    """
    products = Product.objects.all().select_related('category')
    
    # Recherche
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(name__icontains=search_query)
    
    # Filtre par catégorie
    category_filter = request.GET.get('category', '')
    if category_filter:
        products = products.filter(category_id=category_filter)
    
    # Filtre par statut (Optimisé pour rester un QuerySet)
    status_filter = request.GET.get('status', '')
    if status_filter == 'low_stock':
        products = products.filter(quantity__lte=F('alert_threshold'))
    elif status_filter == 'active':
        products = products.filter(quantity__gt=F('alert_threshold'))
    
    # Mode d'affichage (liste ou grille)
    view_mode = request.GET.get('view', 'list')
    
    categories = Category.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'view_mode': view_mode,
    }
    
    return render(request, 'core/product_list.html', context)

@login_required(login_url='login')
def dashboard(request):
    """
    Page d'accueil avec tableau de bord analytique.
    """
    today = timezone.now()
    this_month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Statistiques Clés
    total_revenue_month = Invoice.objects.filter(user=request.user, date__gte=this_month_start).aggregate(total=Sum('total_amount'))['total'] or 0
    total_stock_value = Product.objects.all().aggregate(total=Sum(F('purchase_price') * F('quantity')))['total'] or 0
    low_stock_count = Product.objects.filter(quantity__lte=F('alert_threshold')).count()
    total_customers = Customer.objects.count()
    
    # Activités récentes
    recent_sales = Invoice.objects.filter(user=request.user).select_related('customer').order_by('-date')[:5]
    recent_movements = StockMovement.objects.select_related('product', 'user').order_by('-date')[:5]
    
    # Alertes de stock
    low_stock_products = Product.objects.filter(quantity__lte=F('alert_threshold')).select_related('category')[:5]
    
    context = {
        'revenue': total_revenue_month,
        'stock_value': total_stock_value,
        'low_stock_count': low_stock_count,
        'customer_count': total_customers,
        'recent_sales': recent_sales,
        'recent_movements': recent_movements,
        'low_stock_products': low_stock_products,
        'title': 'Tableau de Bord'
    }
    
    return render(request, 'core/dashboard.html', context)
