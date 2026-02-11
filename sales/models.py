from django.db import models
from django.conf import settings
from django.db.models import Sum
from inventory.models import Product, StockMovement
import datetime

class Customer(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nom")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Téléphone")
    address = models.TextField(blank=True, null=True, verbose_name="Adresse")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"

    def __str__(self):
        return self.name

class Invoice(models.Model):
    class Status(models.TextChoices):
        PAID = "PAID", "Payée"
        UNPAID = "UNPAID", "Impayée"
        PARTIAL = "PARTIAL", "Partiellement payée"
    
    number = models.CharField(max_length=50, unique=True, editable=False, verbose_name="Numéro de facture")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, verbose_name="Client")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Date")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNPAID, verbose_name="Statut")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Montant total")
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Montant payé")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Vendeur")

    class Meta:
        verbose_name = "Facture"
        verbose_name_plural = "Factures"

    def save(self, *args, **kwargs):
        if not self.number:
            year = datetime.date.today().year
            last_invoice = Invoice.objects.filter(number__startswith=str(year)).order_by('id').last()
            if last_invoice:
                try:
                    last_num = int(last_invoice.number.split('-')[-1])
                    new_num = last_num + 1
                except ValueError:
                    new_num = 1
            else:
                new_num = 1
            self.number = f"{year}-{new_num}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Facture {self.number} - {self.customer}"

    @property
    def is_paid(self):
        return self.status == self.Status.PAID

    @property
    def remaining_amount(self):
        return self.total_amount - self.paid_amount

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, verbose_name="Produit")
    quantity = models.IntegerField(verbose_name="Quantité")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix unitaire")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Sous-total")

    class Meta:
        verbose_name = "Ligne de facture"
        verbose_name_plural = "Lignes de facture"

    def save(self, *args, **kwargs):
        self.subtotal = self.unit_price * self.quantity
        
        # Gestion du stock via StockMovement (évite le double décompte)
        if self.pk:
            # Si mise à jour, on ajuste la différence
            old_item = InvoiceItem.objects.get(pk=self.pk)
            diff = self.quantity - old_item.quantity
            if diff != 0:
                StockMovement.objects.create(
                    product=self.product,
                    movement_type='ADJUSTMENT',
                    quantity=-diff, # Si diff > 0 (augmentation vente), mouvement négatif pour le stock
                    reason=f"Correction Vente - Facture {self.invoice.number}",
                    user=self.invoice.user
                )
        else:
            # Nouvelle ligne
            if self.product:
                StockMovement.objects.create(
                    product=self.product,
                    movement_type='EXIT',
                    quantity=self.quantity,
                    reason=f"Vente - Facture {self.invoice.number}",
                    user=self.invoice.user
                )
        
        super().save(*args, **kwargs)
        self.update_invoice_total()

    def delete(self, *args, **kwargs):
        # Restaurer le stock via StockMovement
        if self.product:
            StockMovement.objects.create(
                product=self.product,
                movement_type='ENTRY',
                quantity=self.quantity,
                reason=f"Annulation Ligne - Facture {self.invoice.number}",
                user=self.invoice.user
            )
        
        invoice = self.invoice
        super().delete(*args, **kwargs)
        # Mettre à jour le total de la facture après suppression
        total = invoice.items.aggregate(total=Sum('subtotal'))['total'] or 0
        invoice.total_amount = total
        invoice.save()

    def update_invoice_total(self):
        total = self.invoice.items.aggregate(total=Sum('subtotal'))['total'] or 0
        self.invoice.total_amount = total
        self.invoice.save()
        
    def __str__(self):
        return f"{self.quantity} x {self.product.name if self.product else 'Produit inconnu'}"
