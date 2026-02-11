from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Nom")
    slug = models.SlugField(max_length=100, unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children', verbose_name="Catégorie Parente")
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"

    def __str__(self):
        full_path = [self.name]
        k = self.parent
        while k is not None:
             full_path.append(k.name)
             k = k.parent
        return ' -> '.join(full_path[::-1])

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        
        # Ensure slug uniqueness (if name is unique this is mostly covered, but good to be safe)
        original_slug = self.slug
        queryset = Category.objects.all().exclude(pk=self.pk)
        counter = 1
        while queryset.filter(slug=self.slug).exists():
            self.slug = f"{original_slug}-{counter}"
            counter += 1
            
        super().save(*args, **kwargs)

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.RESTRICT, related_name='products', verbose_name="Catégorie")
    name = models.CharField(max_length=200, verbose_name="Nom")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix d'achat")
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix de vente")
    quantity = models.IntegerField(default=0, verbose_name="Quantité en stock")
    alert_threshold = models.IntegerField(default=10, verbose_name="Seuil d'alerte")
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Image")
    barcode = models.CharField(max_length=100, unique=True, blank=True, null=True, verbose_name="Code-barre")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Produit"
        verbose_name_plural = "Produits"

    def is_low_stock(self):
        return self.quantity <= self.alert_threshold

    def __str__(self):
        return self.name

class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        ENTRY = "ENTRY", "Entrée"
        EXIT = "EXIT", "Sortie"
        ADJUSTMENT = "ADJUSTMENT", "Ajustement"
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements', verbose_name="Produit")
    movement_type = models.CharField(max_length=20, choices=MovementType.choices, verbose_name="Type de mouvement")
    quantity = models.IntegerField(verbose_name="Quantité")
    reason = models.CharField(max_length=255, blank=True, verbose_name="Motif")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Utilisateur")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Date")

    class Meta:
        verbose_name = "Mouvement de stock"
        verbose_name_plural = "Mouvements de stock"

    def save(self, *args, **kwargs):
        if not self.pk:  # Only on creation
            if self.movement_type == self.MovementType.ENTRY:
                self.product.quantity += self.quantity
            elif self.movement_type == self.MovementType.EXIT:
                self.product.quantity -= self.quantity
            elif self.movement_type == self.MovementType.ADJUSTMENT:
                # Adjustment can be positive or negative, assumption: quantity is signed or absolute?
                # Usually adjustment means settng to a value or adding/subtracting.
                # Here let's assume quantity is "change amount". 
                # If the user wants to set stock to X, we calculate diff. 
                # But here we store "movements". So quantity should be the change.
                # Let's assume quantity is always positive, and type dictates sign?
                # Actually for Adjustment, it's safer to allow negative quantity?
                # To simplify: Entry/Exit use positive quantity. Adjustment can use positive/negative.
                self.product.quantity += self.quantity

            self.product.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_movement_type_display()} {self.quantity} - {self.product.name}"
