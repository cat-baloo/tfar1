
# core/admin.py
from django.contrib import admin
from .models import Client, ClientMembership, TfarRecord, UserProfile, TfarUpload, TfarExport

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

@admin.register(ClientMembership)
class ClientMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "client", "role")
    list_filter = ("role", "client")
    search_fields = ("user__username", "client__name")

@admin.register(TfarRecord)
class TfarRecordAdmin(admin.ModelAdmin):
    list_display = ("asset_id", "client", "owner", "uploaded_at", "purchase_cost", "closing_wdv")
    list_filter = ("client", "depreciation_method")
    search_fields = ("asset_id", "asset_description")

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "user_type")

@admin.register(TfarUpload)
class TfarUploadAdmin(admin.ModelAdmin):
    list_display = ("client", "uploaded_by", "original_filename", "row_count", "source_ip", "created_at")
    list_filter = ("client", "uploaded_by")
    search_fields = ("original_filename",)

@admin.register(TfarExport)
class TfarExportAdmin(admin.ModelAdmin):
    list_display = ("client", "exported_by", "filename", "row_count", "created_at")
    list_filter = ("client", "exported_by")
    search_fields = ("filename",)
