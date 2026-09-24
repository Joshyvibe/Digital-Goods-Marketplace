from django.db.models import Count, F, Sum
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsVendor
from apps.catalog.models import Product

from . import services
from .models import Order, VendorSuborder
from .serializers import AddCartItemSerializer, CartSerializer, OrderSerializer, VendorSaleSerializer
from .services import CartError, CheckoutError


class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        cart = services.get_or_create_open_cart(request.user)
        return Response(CartSerializer(cart).data)


class CartItemView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            product = Product.objects.select_related("vendor").get(
                id=serializer.validated_data["product_id"]
            )
        except Product.DoesNotExist:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        cart = services.get_or_create_open_cart(request.user)
        try:
            services.add_item_to_cart(cart, product)
        except CartError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)

    def delete(self, request, product_id, *args, **kwargs):
        cart = services.get_or_create_open_cart(request.user)
        services.remove_item_from_cart(cart, product_id)
        return Response(CartSerializer(cart).data)


class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        cart = services.get_or_create_open_cart(request.user)

        try:
            order, checkout_urls = services.checkout_cart(cart)
        except CheckoutError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"order_id": order.id, "checkout_urls": checkout_urls})


class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(buyer=self.request.user).order_by("-created_at")


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(buyer=self.request.user)


class SuborderRetryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id, suborder_id, *args, **kwargs):
        try:
            suborder = VendorSuborder.objects.get(
                id=suborder_id, order_id=order_id, order__buyer=request.user
            )
        except VendorSuborder.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            checkout_urls = services.retry_suborder_checkout(suborder)
        except CheckoutError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"checkout_urls": checkout_urls})


class SuborderCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, order_id, suborder_id, *args, **kwargs):
        try:
            suborder = VendorSuborder.objects.get(
                id=suborder_id, order_id=order_id, order__buyer=request.user
            )
        except VendorSuborder.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            services.cancel_pending_suborder(suborder)
        except CheckoutError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)


class VendorSalesView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsVendor]

    def get(self, request, *args, **kwargs):
        suborders = (
            VendorSuborder.objects.filter(vendor=request.user.vendor_profile)
            .select_related("order__buyer")
            .prefetch_related("line_items")
            .order_by("-order__created_at")
        )

        paid = suborders.filter(status="paid")
        totals = paid.aggregate(
            net_cents=Sum(F("subtotal_cents") - F("platform_fee_cents")),
            sale_count=Count("id"),
        )

        summary = {
            "total_earned_cents": totals["net_cents"] or 0,
            "total_sales": totals["sale_count"] or 0,
            "pending_count": suborders.filter(status="pending").count(),
        }

        return Response({"summary": summary, "sales": VendorSaleSerializer(suborders, many=True).data})
