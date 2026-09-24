from rest_framework import serializers

from .models import Cart, CartItem, Order, OrderLineItem, VendorSuborder


class CartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    title = serializers.CharField(source="product.title", read_only=True)
    slug = serializers.CharField(source="product.slug", read_only=True)
    price_cents = serializers.IntegerField(source="product.price_cents", read_only=True)
    currency = serializers.CharField(source="product.currency", read_only=True)
    vendor_store_name = serializers.CharField(source="product.vendor.store_name", read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "product_id", "title", "slug", "price_cents", "currency", "vendor_store_name"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_cents = serializers.SerializerMethodField()
    vendor_count = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "status", "items", "total_cents", "vendor_count"]

    def get_total_cents(self, obj: Cart) -> int:
        return sum(item.product.price_cents for item in obj.items.all())

    def get_vendor_count(self, obj: Cart) -> int:
        return len({item.product.vendor_id for item in obj.items.all()})


class AddCartItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()


class OrderLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderLineItem
        fields = ["id", "product_title_snapshot", "unit_price_cents"]


class VendorSuborderSerializer(serializers.ModelSerializer):
    vendor_store_name = serializers.CharField(source="vendor.store_name", read_only=True)
    line_items = OrderLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = VendorSuborder
        fields = [
            "id",
            "vendor_store_name",
            "subtotal_cents",
            "status",
            "paid_at",
            "line_items",
        ]


class OrderSerializer(serializers.ModelSerializer):
    suborders = VendorSuborderSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "status", "total_cents", "currency", "created_at", "suborders"]


class VendorSaleSerializer(serializers.ModelSerializer):
    # Vendor-facing view of a suborder — the mirror image of VendorSuborderSerializer
    # (buyer-facing) above: surfaces who bought it and the net payout, never the buyer's
    # other order history or payment details.
    order_id = serializers.IntegerField(source="order.id", read_only=True)
    buyer_email = serializers.EmailField(source="order.buyer.email", read_only=True)
    created_at = serializers.DateTimeField(source="order.created_at", read_only=True)
    net_cents = serializers.SerializerMethodField()
    line_items = OrderLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = VendorSuborder
        fields = [
            "id",
            "order_id",
            "buyer_email",
            "status",
            "subtotal_cents",
            "platform_fee_cents",
            "net_cents",
            "created_at",
            "paid_at",
            "line_items",
        ]

    def get_net_cents(self, obj: VendorSuborder) -> int:
        return obj.subtotal_cents - obj.platform_fee_cents
