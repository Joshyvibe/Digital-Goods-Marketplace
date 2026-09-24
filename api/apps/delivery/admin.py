from django.contrib import admin

from .models import DownloadGrant


@admin.register(DownloadGrant)
class DownloadGrantAdmin(admin.ModelAdmin):
    list_display = ["id", "buyer", "product_file", "created_at", "revoked_at"]
    list_filter = ["revoked_at"]
    search_fields = ["buyer__email"]
