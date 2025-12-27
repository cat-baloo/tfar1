
# core/models.py
from django.conf import settings
from django.db import models


class Client(models.Model):
    name = models.CharField(max_length=150, unique=True)
    def __str__(self):
        return self.name


class ClientMembership(models.Model):
    ROLE_CHOICES = (
        ("preparer", "Preparer"),
        ("reviewer", "Reviewer"),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="preparer")

    class Meta:
        unique_together = ("user", "client")

    def __str__(self):
        return f"{self.user.username} → {self.client.name} ({self.role})"


class UserProfile(models.Model):
    USER_TYPES = (("type1", "Type 1"), ("type2", "Type 2"))
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default="type1")
    def __str__(self):
        return f"{self.user.username} ({self.user_type})"


class TfarRecord(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)

    # 15 TFAR fields
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
        indexes = [
            models.Index(fields=["client", "owner", "asset_id"], name="core_client_owner_asset_idx"),
        ]

    def __str__(self):
        return f"[{self.client.name}] {self.asset_id}"


# ---------- Audit models ----------

class TfarUpload(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    original_filename = models.CharField(max_length=255)
    row_count = models.IntegerField(default=0)
    source_ip = models.CharField(max_length=64, blank=True, default="")  # proxy-safe best effort
    checksum = models.CharField(max_length=128, blank=True, default="")  # optional SHA256 of file
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["client", "uploaded_by", "created_at"])]

    def __str__(self):
        return f"Upload [{self.client.name}] rows={self.row_count} by {self.uploaded_by}"


class TfarExport(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    exported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)
    row_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["client", "exported_by", "created_at"])]

    def __str__(self):
        return f"Export [{self.client.name}] rows={self.row_count} by {self.exported_by}"
