from django.contrib import admin
from .models import Category, Product, StockMovement

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'purchase_price', 'selling_price', 'quantity', 'alert_threshold', 'is_low_stock')
    list_filter = ('category', 'created_at')
    search_fields = ('name', 'barcode', 'description')
    list_editable = ('selling_price', 'alert_threshold')
    # quantity is editable here but ideally should be read-only to force using movements. 
    # For simplicity, let's keep it editable but warn user or make read-only.
    # To secure stock, make quantity read-only and force usage of StockMovements via inlines or separate admin.
    readonly_fields = ('created_at', 'updated_at')

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'movement_type', 'quantity', 'date', 'user')
    list_filter = ('movement_type', 'date', 'user')
    search_fields = ('product__name', 'reason')
    date_hierarchy = 'date'
