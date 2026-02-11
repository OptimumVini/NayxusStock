from django.db.models import F
from .models import StoreSettings
from inventory.models import Product

def store_info(request):
    """Fournit les informations du magasin à tous les templates"""
    return {
        'store': StoreSettings.get_settings()
    }

def stock_alerts(request):
    """Compte le nombre de produits en alerte de stock"""
    count = Product.objects.filter(quantity__lte=F('alert_threshold')).count()
    return {
        'low_stock_alert_count': count
    }
