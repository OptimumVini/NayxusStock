from django import forms
from django.forms import inlineformset_factory
from .models import Invoice, InvoiceItem

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['customer', 'total_amount', 'paid_amount', 'status']
        widgets = {
            'total_amount': forms.NumberInput(attrs={'readonly': 'readonly'}),
        }

class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['product', 'quantity', 'unit_price', 'subtotal']
        widgets = {
            'unit_price': forms.NumberInput(attrs={'step': '0.01'}),
            'subtotal': forms.NumberInput(attrs={'readonly': 'readonly'}),
        }

InvoiceItemFormSet = inlineformset_factory(
    Invoice, InvoiceItem,
    form=InvoiceItemForm,
    extra=1,
    can_delete=True
)
