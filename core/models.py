from django.db import models

class StoreSettings(models.Model):
    name = models.CharField(max_length=100, default="NayxusStock", verbose_name="Nom du magasin")
    address = models.TextField(blank=True, null=True, verbose_name="Adresse")
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Téléphone")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    logo = models.ImageField(upload_to='logo/', blank=True, null=True, verbose_name="Logo")

    class Meta:
        verbose_name = "Paramètres du magasin"
        verbose_name_plural = "Paramètres du magasin"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # On s'assure qu'un seul enregistrement existe (id=1)
        self.id = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(id=1)
        return obj
