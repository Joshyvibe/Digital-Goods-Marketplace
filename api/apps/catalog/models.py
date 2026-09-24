from django.db import models

from apps.accounts.models import VendorProfile

CATEGORY_CHOICES = [
    ("template", "Template"),
    ("preset", "Preset"),
    ("ebook", "Ebook"),
    ("license", "License"),
    ("stock", "Stock Asset"),
]


class PublishedProductManager(models.Manager):
    # The only queryset the public catalog API is allowed to touch — draft/archived
    # products, and anything from a vendor that can't yet accept payment, can't leak
    # through a generic .all() call because public views never import that manager.
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(status="published", vendor__charges_enabled=True)
        )


class Product(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]

    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name="products")
    title = models.CharField(max_length=200)
    slug = models.SlugField()
    description = models.TextField()
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES)
    price_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="usd")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    cover_image_key = models.CharField(max_length=512, blank=True)  # R2 key, preview asset
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["vendor", "slug"], name="uniq_vendor_product_slug")
        ]
        ordering = ["-created_at"]

    objects = models.Manager()
    published = PublishedProductManager()

    def __str__(self):
        return self.title


class ProductFile(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="files")
    storage_key = models.CharField(max_length=512)  # private R2 key, never exposed directly
    original_filename = models.CharField(max_length=255)
    byte_size = models.BigIntegerField()
    content_type = models.CharField(max_length=127)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.original_filename
