from django.contrib import admin
from .models import Customer, Invoice, InvoiceItem

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'address')
    search_fields = ('name', 'email', 'phone')

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('number', 'customer', 'date', 'total_amount', 'paid_amount', 'status', 'user')
    list_filter = ('status', 'date', 'user')
    search_fields = ('number', 'customer__name')
    date_hierarchy = 'date'
    inlines = [InvoiceItemInline]
    readonly_fields = ('number', 'date', 'user')

    def save_model(self, request, obj, form, change):
        if not obj.user:
            obj.user = request.user
        super().save_model(request, obj, form, change)
