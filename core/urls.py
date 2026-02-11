from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('products/', views.product_list, name='product_list'),
    path('settings/', views.StoreSettingsUpdateView.as_view(), name='store_settings'),
]
