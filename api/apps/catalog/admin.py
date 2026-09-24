from django.contrib import admin

from .models import Product, ProductFile


class ProductFileInline(admin.TabularInline):
    model = ProductFile
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["title", "vendor", "category", "status", "price_cents"]
    list_filter = ["status", "category"]
    search_fields = ["title", "vendor__store_name"]
    inlines = [ProductFileInline]
