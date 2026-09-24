from rest_framework.test import APITestCase

from apps.accounts.models import User, VendorProfile
from apps.catalog.models import Product
from apps.orders.models import Order, OrderLineItem, VendorSuborder


def _vendor(email: str, store_name: str) -> VendorProfile:
    user = User.objects.create_user(email=email, password="s3cure-pass-1")
    return VendorProfile.objects.create(
        user=user, store_name=store_name, slug=store_name.lower().replace(" ", "-"),
        charges_enabled=True, payouts_enabled=True, stripe_account_id="acct_fake",
    )


def _suborder(vendor, buyer, subtotal_cents, platform_fee_cents, status_):
    product = Product.objects.create(
        vendor=vendor, title="Widget", slug=f"widget-{VendorSuborder.objects.count()}",
        description="", category="template", price_cents=subtotal_cents,
    )
    order = Order.objects.create(buyer=buyer, total_cents=subtotal_cents, currency="usd")
    suborder = VendorSuborder.objects.create(
        order=order, vendor=vendor, subtotal_cents=subtotal_cents,
        platform_fee_cents=platform_fee_cents, status=status_,
    )
    OrderLineItem.objects.create(
        suborder=suborder, product=product, unit_price_cents=subtotal_cents,
        product_title_snapshot=product.title,
    )
    return suborder


class VendorSalesViewTests(APITestCase):
    def test_requires_vendor(self):
        buyer = User.objects.create_user(email="buyer@example.com", password="s3cure-pass-1")
        self.client.force_authenticate(buyer)

        response = self.client.get("/api/vendors/sales/")

        self.assertEqual(response.status_code, 403)

    def test_vendor_sees_only_their_own_sales_with_correct_summary(self):
        vendor = _vendor("v1@example.com", "Vendor One")
        other_vendor = _vendor("v2@example.com", "Vendor Two")
        buyer = User.objects.create_user(email="buyer1@example.com", password="s3cure-pass-1")

        _suborder(vendor, buyer, 1000, 150, "paid")
        _suborder(vendor, buyer, 2000, 300, "paid")
        _suborder(vendor, buyer, 500, 75, "pending")
        _suborder(other_vendor, buyer, 9999, 1000, "paid")

        self.client.force_authenticate(vendor.user)
        response = self.client.get("/api/vendors/sales/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["sales"]), 3)
        self.assertEqual(response.data["summary"]["total_earned_cents"], (1000 - 150) + (2000 - 300))
        self.assertEqual(response.data["summary"]["total_sales"], 2)
        self.assertEqual(response.data["summary"]["pending_count"], 1)

    def test_sale_includes_buyer_email_and_line_items(self):
        vendor = _vendor("v3@example.com", "Vendor Three")
        buyer = User.objects.create_user(email="buyer3@example.com", password="s3cure-pass-1")
        _suborder(vendor, buyer, 1000, 150, "paid")

        self.client.force_authenticate(vendor.user)
        response = self.client.get("/api/vendors/sales/")

        sale = response.data["sales"][0]
        self.assertEqual(sale["buyer_email"], "buyer3@example.com")
        self.assertEqual(sale["net_cents"], 850)
        self.assertEqual(len(sale["line_items"]), 1)
        self.assertEqual(sale["line_items"][0]["product_title_snapshot"], "Widget")
