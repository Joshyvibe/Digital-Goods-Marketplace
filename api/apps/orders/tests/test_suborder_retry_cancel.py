from unittest.mock import MagicMock, patch

from rest_framework.test import APITestCase

from apps.accounts.models import User, VendorProfile
from apps.catalog.models import Product
from apps.orders.models import Order, OrderLineItem, VendorSuborder
from apps.orders.services import CheckoutError, cancel_pending_suborder, retry_suborder_checkout


def _vendor(email: str, store_name: str, charges_enabled=True) -> VendorProfile:
    user = User.objects.create_user(email=email, password="s3cure-pass-1")
    return VendorProfile.objects.create(
        user=user, store_name=store_name, slug=store_name.lower().replace(" ", "-"),
        charges_enabled=charges_enabled, payouts_enabled=charges_enabled,
        stripe_account_id="acct_fake" if charges_enabled else "",
    )


def _pending_suborder(buyer, vendor, price_cents=1000, product_status="published"):
    product = Product.objects.create(
        vendor=vendor, title="Widget", slug=f"widget-{VendorSuborder.objects.count()}",
        description="d", category="template", price_cents=price_cents, status=product_status,
    )
    order = Order.objects.create(buyer=buyer, total_cents=price_cents, currency="usd")
    suborder = VendorSuborder.objects.create(
        order=order, vendor=vendor, subtotal_cents=price_cents, platform_fee_cents=round(price_cents * 0.15),
        status="pending",
    )
    OrderLineItem.objects.create(
        suborder=suborder, product=product, unit_price_cents=price_cents,
        product_title_snapshot=product.title,
    )
    return suborder


class RetrySuborderCheckoutServiceTests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(email="buyer@example.com", password="s3cure-pass-1")

    @patch("apps.orders.services.stripe.checkout.Session.create")
    def test_retry_creates_a_fresh_session_for_a_pending_suborder(self, mock_create):
        vendor = _vendor("v1@example.com", "Vendor One")
        suborder = _pending_suborder(self.buyer, vendor)
        mock_create.return_value = MagicMock(
            id="cs_new", url="https://checkout.stripe.com/new", payment_intent=None
        )

        urls = retry_suborder_checkout(suborder)

        self.assertEqual(urls, ["https://checkout.stripe.com/new"])
        suborder.refresh_from_db()
        self.assertEqual(suborder.stripe_checkout_session_id, "cs_new")
        self.assertEqual(mock_create.call_count, 1)

    def test_cannot_retry_a_non_pending_suborder(self):
        vendor = _vendor("v2@example.com", "Vendor Two")
        suborder = _pending_suborder(self.buyer, vendor)
        suborder.status = "paid"
        suborder.save(update_fields=["status"])

        with self.assertRaises(CheckoutError):
            retry_suborder_checkout(suborder)

    def test_cannot_retry_if_product_no_longer_available(self):
        vendor = _vendor("v3@example.com", "Vendor Three")
        suborder = _pending_suborder(self.buyer, vendor, product_status="archived")

        with self.assertRaises(CheckoutError):
            retry_suborder_checkout(suborder)

    def test_cannot_retry_if_vendor_lost_charges_enabled(self):
        vendor = _vendor("v4@example.com", "Vendor Four", charges_enabled=False)
        suborder = _pending_suborder(self.buyer, vendor)

        with self.assertRaises(CheckoutError):
            retry_suborder_checkout(suborder)


class CancelPendingSuborderServiceTests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(email="buyer2@example.com", password="s3cure-pass-1")

    def test_cancel_deletes_the_order_when_it_was_the_only_suborder(self):
        vendor = _vendor("v5@example.com", "Vendor Five")
        suborder = _pending_suborder(self.buyer, vendor)
        order_id = suborder.order_id

        cancel_pending_suborder(suborder)

        self.assertFalse(Order.objects.filter(id=order_id).exists())
        self.assertFalse(VendorSuborder.objects.filter(id=suborder.id).exists())

    def test_cancel_keeps_order_and_recomputes_total_when_siblings_remain(self):
        vendor_a = _vendor("v6@example.com", "Vendor Six")
        vendor_b = _vendor("v7@example.com", "Vendor Seven")
        suborder_a = _pending_suborder(self.buyer, vendor_a, price_cents=1000)
        order = suborder_a.order
        suborder_b = VendorSuborder.objects.create(
            order=order, vendor=vendor_b, subtotal_cents=2000, platform_fee_cents=300, status="paid",
        )
        order.total_cents = 3000
        order.save(update_fields=["total_cents"])

        cancel_pending_suborder(suborder_a)

        order.refresh_from_db()
        self.assertEqual(order.total_cents, 2000)
        self.assertTrue(VendorSuborder.objects.filter(id=suborder_b.id).exists())
        self.assertFalse(VendorSuborder.objects.filter(id=suborder_a.id).exists())

    def test_cannot_cancel_a_paid_suborder(self):
        vendor = _vendor("v8@example.com", "Vendor Eight")
        suborder = _pending_suborder(self.buyer, vendor)
        suborder.status = "paid"
        suborder.save(update_fields=["status"])

        with self.assertRaises(CheckoutError):
            cancel_pending_suborder(suborder)

        self.assertTrue(VendorSuborder.objects.filter(id=suborder.id).exists())


class SuborderRetryCancelApiTests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(email="buyer3@example.com", password="s3cure-pass-1")
        login = self.client.post(
            "/api/auth/token/", {"email": "buyer3@example.com", "password": "s3cure-pass-1"}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    @patch("apps.orders.services.stripe.checkout.Session.create")
    def test_retry_endpoint_returns_checkout_urls(self, mock_create):
        vendor = _vendor("v9@example.com", "Vendor Nine")
        suborder = _pending_suborder(self.buyer, vendor)
        mock_create.return_value = MagicMock(
            id="cs_api", url="https://checkout.stripe.com/api", payment_intent=None
        )

        response = self.client.post(
            f"/api/orders/{suborder.order_id}/suborders/{suborder.id}/retry/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["checkout_urls"], ["https://checkout.stripe.com/api"])

    def test_cancel_endpoint_returns_204(self):
        vendor = _vendor("v10@example.com", "Vendor Ten")
        suborder = _pending_suborder(self.buyer, vendor)

        response = self.client.delete(
            f"/api/orders/{suborder.order_id}/suborders/{suborder.id}/"
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(VendorSuborder.objects.filter(id=suborder.id).exists())

    def test_cannot_retry_or_cancel_another_buyers_suborder(self):
        stranger = User.objects.create_user(email="stranger2@example.com", password="s3cure-pass-1")
        vendor = _vendor("v11@example.com", "Vendor Eleven")
        suborder = _pending_suborder(stranger, vendor)

        retry_response = self.client.post(
            f"/api/orders/{suborder.order_id}/suborders/{suborder.id}/retry/"
        )
        cancel_response = self.client.delete(
            f"/api/orders/{suborder.order_id}/suborders/{suborder.id}/"
        )

        self.assertEqual(retry_response.status_code, 404)
        self.assertEqual(cancel_response.status_code, 404)
        self.assertTrue(VendorSuborder.objects.filter(id=suborder.id).exists())
