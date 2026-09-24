from django.db import models

from apps.accounts.models import User, VendorProfile
from apps.catalog.models import Product


class Cart(models.Model):
    STATUS_CHOICES = [("open", "Open"), ("converted", "Converted")]

    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="carts")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart({self.buyer_id}, {self.status})"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="uniq_cart_product")
        ]


class Order(models.Model):
    # Buyer-facing whole; may fan out into multiple VendorSuborders for a multi-vendor cart.
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("partially_paid", "Partially Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    buyer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    total_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="usd")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} ({self.status})"


class VendorSuborder(models.Model):
    # The actual unit of Stripe interaction — one Checkout Session per suborder, since a
    # PaymentIntent has exactly one transfer_data.destination (see SYSTEM_DESIGN/PLAN §2).
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="suborders")
    vendor = models.ForeignKey(VendorProfile, on_delete=models.PROTECT, related_name="suborders")
    subtotal_cents = models.PositiveIntegerField()
    platform_fee_cents = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    stripe_checkout_session_id = models.CharField(max_length=128, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=128, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Suborder #{self.id} ({self.vendor_id}, {self.status})"


class OrderLineItem(models.Model):
    suborder = models.ForeignKey(VendorSuborder, on_delete=models.CASCADE, related_name="line_items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    unit_price_cents = models.PositiveIntegerField()  # price snapshot at purchase time
    product_title_snapshot = models.CharField(max_length=200)  # survives product edits/deletion
