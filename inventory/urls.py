from django.urls import path
from .views import (
    category_list, stock_movement_list, ProductCreateView,
    CategoryCreateView, StockMovementCreateView,
    ProductDetailView, ProductUpdateView,
    CategoryDetailView, CategoryUpdateView, CategoryDeleteView,
    StockMovementDetailView, product_detail_json,
    export_products_csv, stock_entry_report, inventory_report
)

urlpatterns = [
    path('categories/', category_list, name='category_list'),
    path('categories/add/', CategoryCreateView.as_view(), name='category_add'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category_detail'),
    path('categories/<int:pk>/edit/', CategoryUpdateView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', CategoryDeleteView.as_view(), name='category_delete'),
    path('mouvements/', stock_movement_list, name='stock_movement_list'),
    path('mouvements/add/', StockMovementCreateView.as_view(), name='stock_movement_add'),
    path('mouvements/<int:pk>/', StockMovementDetailView.as_view(), name='stock_movement_detail'),
    path('products/add/', ProductCreateView.as_view(), name='product_add'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product_detail'),
    path('products/<int:pk>/edit/', ProductUpdateView.as_view(), name='product_edit'),
    path('api/products/<int:pk>/', product_detail_json, name='product_api_detail'),
    path('products/export/csv/', export_products_csv, name='export_products_csv'),
    path('products/report/entries/', stock_entry_report, name='stock_entry_report'),
    path('products/report/inventory/', inventory_report, name='inventory_report'),
]
