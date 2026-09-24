import uuid

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import VendorProfile
from apps.accounts.permissions import IsVendor
from apps.delivery.r2_client import R2NotConfiguredError, generate_presigned_put

from .models import Product
from .serializers import (
    PresignUploadRequestSerializer,
    ProductFileCreateSerializer,
    ProductFileSerializer,
    PublicProductSerializer,
    VendorProductSerializer,
    VendorStorefrontSerializer,
)


class PublicProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Storefront-facing, read-only. Uses Product.published exclusively — draft/archived
    products and anything from an unpaid-out vendor cannot appear here (see
    PublishedProductManager)."""

    queryset = Product.published.all()
    serializer_class = PublicProductSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get("category")
        search = self.request.query_params.get("search")
        if category:
            queryset = queryset.filter(category=category)
        if search:
            queryset = queryset.filter(title__icontains=search)
        return queryset


class VendorStorefrontView(APIView):
    """GET /api/store/{slug}/ — the public, shareable page for one vendor's shop. Looked up
    regardless of charges_enabled (a vendor can share their link while still onboarding —
    it'll just show no products yet, not a 404), but the products list itself still only
    ever comes from Product.published, so nothing not-yet-payable can appear there."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, slug, *args, **kwargs):
        try:
            vendor = VendorProfile.objects.get(slug=slug)
        except VendorProfile.DoesNotExist:
            return Response({"detail": "Store not found."}, status=status.HTTP_404_NOT_FOUND)

        products = Product.published.filter(vendor=vendor)
        return Response(
            {
                **VendorStorefrontSerializer(vendor).data,
                "products": PublicProductSerializer(products, many=True).data,
            }
        )


class VendorProductViewSet(viewsets.ModelViewSet):
    """Vendor-scoped CRUD — deliberately a separate viewset from PublicProductViewSet
    (different permissions, different queryset, different serializer) rather than one
    viewset with conditional logic (see SYSTEM_DESIGN.md §4)."""

    serializer_class = VendorProductSerializer
    permission_classes = [permissions.IsAuthenticated, IsVendor]

    def get_queryset(self):
        return Product.objects.filter(vendor=self.request.user.vendor_profile)

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "request": self.request}

    @action(detail=True, methods=["post"], url_path="presign-upload")
    def presign_upload(self, request, pk=None):
        """Step 1 of upload: mint a presigned R2 PUT URL. The client uploads bytes
        directly to R2 (never through this server), then calls the `files` action below
        to register the resulting file — this server never sees the file body itself."""
        product = self.get_object()
        serializer = PresignUploadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        storage_key = (
            f"products/{product.id}/files/{uuid.uuid4().hex}/"
            f"{serializer.validated_data['filename']}"
        )
        try:
            upload_url = generate_presigned_put(
                storage_key, serializer.validated_data["content_type"]
            )
        except R2NotConfiguredError:
            return Response(
                {"detail": "File storage is not configured."}, status=status.HTTP_502_BAD_GATEWAY
            )

        return Response({"upload_url": upload_url, "storage_key": storage_key})

    @action(detail=True, methods=["post"], url_path="files")
    def add_file(self, request, pk=None):
        """Step 2 of upload: register a ProductFile row for a key the client already
        uploaded to R2 via the presigned URL above."""
        product = self.get_object()
        serializer = ProductFileCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_file = serializer.save(product=product, sort_order=product.files.count())
        return Response(ProductFileSerializer(product_file).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=r"files/(?P<file_id>\d+)")
    def delete_file(self, request, pk=None, file_id=None):
        product = self.get_object()
        deleted, _ = product.files.filter(id=file_id).delete()
        if not deleted:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
