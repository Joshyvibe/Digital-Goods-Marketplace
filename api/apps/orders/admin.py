from django.contrib import admin

from .models import Cart, CartItem, Order, OrderLineItem, VendorSuborder


class OrderLineItemInline(admin.TabularInline):
    model = OrderLineItem
    extra = 0


class VendorSuborderInline(admin.TabularInline):
    model = VendorSuborder
    extra = 0
    show_change_link = True


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "buyer", "status", "total_cents", "created_at"]
    list_filter = ["status"]
    inlines = [VendorSuborderInline]


@admin.register(VendorSuborder)
class VendorSuborderAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "vendor", "status", "subtotal_cents", "platform_fee_cents"]
    list_filter = ["status"]
    inlines = [OrderLineItemInline]


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["id", "buyer", "status", "created_at"]
    list_filter = ["status"]
    inlines = [CartItemInline]
