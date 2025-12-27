
from django.conf import settings
from django.db import models

class UserProfile(models.Model):
    USER_TYPES = (("type1", "Type 1"), ("type2", "Type 2"))
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default="type1")
    def __str__(self): return f"{self.user.username} ({self.user_type})"

class TfarRecord(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    asset_id = models.CharField(max_length=50)
    asset_description = models.CharField(max_length=250)
    tax_start_date = models.DateField()
    depreciation_method = models.CharField(max_length=50)
    purchase_cost = models.IntegerField()
    tax_effective_life = models.IntegerField()
    opening_cost = models.IntegerField()
    opening_accum_depreciation = models.IntegerField()
    opening_wdv = models.IntegerField()
    addition = models.IntegerField()
    disposal = models.IntegerField()
    tax_depreciation = models.IntegerField()
    closing_cost = models.IntegerField()
    closing_accum_depreciation = models.IntegerField()
    closing_wdv = models.IntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [models.Index(fields=["owner", "asset_id"])]
