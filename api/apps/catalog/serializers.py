from rest_framework import serializers

from django.utils.text import slugify

from apps.accounts.models import VendorProfile
from apps.delivery.r2_client import R2NotConfiguredError, generate_presigned_get

from .models import Product, ProductFile


class CoverImageUrlMixin(serializers.Serializer):
    cover_image_url = serializers.SerializerMethodField()

    def get_cover_image_url(self, obj: Product) -> str | None:
        # The bucket is fully private (see delivery/r2_client.py) — even a "public" preview
        # image is served through a signed URL, just with a longer, low-stakes expiry than
        # a paid-file download gets.
        if not obj.cover_image_key:
            return None
        try:
            return generate_presigned_get(obj.cover_image_key, expires_in=3600)
        except R2NotConfiguredError:
            return None


class PublicProductSerializer(CoverImageUrlMixin, serializers.ModelSerializer):
    # Deliberately hand-picked fields, not "= '__all__'" — vendor.stripe_account_id has no
    # path to leak through this serializer because it was never declared on it.
    vendor_store_name = serializers.CharField(source="vendor.store_name", read_only=True)
    vendor_slug = serializers.CharField(source="vendor.slug", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "vendor_store_name",
            "vendor_slug",
            "title",
            "slug",
            "description",
            "category",
            "price_cents",
            "currency",
            "cover_image_url",
        ]


class VendorStorefrontSerializer(serializers.ModelSerializer):
    # Public storefront card — only ever what a stranger visiting a shared store link
    # should see. No stripe_account_id, no email, nothing internal.
    class Meta:
        model = VendorProfile
        fields = ["store_name", "slug"]


class ProductFileSerializer(serializers.ModelSerializer):
    # storage_key is deliberately absent — never exposed directly (see PLAN.md §3).
    class Meta:
        model = ProductFile
        fields = ["id", "original_filename", "byte_size", "content_type", "sort_order"]
        read_only_fields = fields


class VendorProductSerializer(CoverImageUrlMixin, serializers.ModelSerializer):
    """Vendor-facing CRUD shape — the one place `cover_image_key` and `status` are
    writable. Never reused for the public catalog (see PublicProductSerializer)."""

    files = ProductFileSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "category",
            "price_cents",
            "currency",
            "status",
            "cover_image_key",
            "cover_image_url",
            "files",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]

    def validate_status(self, value):
        if value == "published":
            vendor = self.context["request"].user.vendor_profile
            if not vendor.charges_enabled:
                raise serializers.ValidationError(
                    "Complete Stripe onboarding before publishing products."
                )
        return value

    def create(self, validated_data):
        vendor = self.context["request"].user.vendor_profile
        base_slug = slugify(validated_data["title"])
        slug = base_slug
        suffix = 1
        while Product.objects.filter(vendor=vendor, slug=slug).exists():
            suffix += 1
            slug = f"{base_slug}-{suffix}"

        validated_data["vendor"] = vendor
        validated_data["slug"] = slug
        return super().create(validated_data)


class PresignUploadRequestSerializer(serializers.Serializer):
    filename = serializers.CharField(max_length=255)
    content_type = serializers.CharField(max_length=127)


class ProductFileCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFile
        fields = ["storage_key", "original_filename", "byte_size", "content_type"]
