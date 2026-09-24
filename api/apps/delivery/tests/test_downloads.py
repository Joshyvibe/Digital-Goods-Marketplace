from unittest.mock import patch

from rest_framework.test import APITestCase

from apps.accounts.models import User, VendorProfile
from apps.catalog.models import Product, ProductFile
from apps.delivery.models import DownloadGrant
from apps.orders.models import Order, OrderLineItem, VendorSuborder
from apps.payments.stripe_client import stripe


def _vendor(email, store_name) -> VendorProfile:
    user = User.objects.create_user(email=email, password="s3cure-pass-1")
    return VendorProfile.objects.create(
        user=user, store_name=store_name, slug=store_name.lower().replace(" ", "-"),
        charges_enabled=True, payouts_enabled=True, stripe_account_id="acct_fake",
    )


def _paid_order_with_file(vendor, buyer, session_id="cs_test1", pi_id="pi_test1"):
    product = Product.objects.create(
        vendor=vendor, title="Icon Pack", slug="icon-pack", description="",
        category="template", price_cents=1000,
    )
    product_file = ProductFile.objects.create(
        product=product, storage_key="products/1/files/1/pack.zip",
        original_filename="pack.zip", byte_size=100, content_type="application/zip",
    )
    order = Order.objects.create(buyer=buyer, total_cents=1000, currency="usd")
    suborder = VendorSuborder.objects.create(
        order=order, vendor=vendor, subtotal_cents=1000, platform_fee_cents=150,
        status="pending", stripe_checkout_session_id=session_id, stripe_payment_intent_id=pi_id,
    )
    OrderLineItem.objects.create(
        suborder=suborder, product=product, unit_price_cents=1000, product_title_snapshot=product.title,
    )
    return order, suborder, product_file


def _stripe_event(event_id: str, event_type: str, obj: dict):
    return stripe.Event.construct_from(
        {"id": event_id, "type": event_type, "data": {"object": obj}}, "fake_api_key"
    )


class DownloadGrantWebhookTests(APITestCase):
    @patch("apps.payments.views.stripe.Webhook.construct_event")
    def test_checkout_completed_grants_downloads(self, mock_construct):
        vendor = _vendor("v1@example.com", "Vendor One")
        buyer = User.objects.create_user(email="buyer1@example.com", password="s3cure-pass-1")
        order, suborder, product_file = _paid_order_with_file(vendor, buyer)
        mock_construct.return_value = _stripe_event(
            "evt_1", "checkout.session.completed", {"id": "cs_test1", "payment_intent": "pi_test1"}
        )

        response = self.client.post(
            "/api/webhooks/stripe/", data=b"{}", content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )

        self.assertEqual(response.status_code, 200)
        grant = DownloadGrant.objects.get(buyer=buyer, product_file=product_file)
        self.assertIsNone(grant.revoked_at)

    @patch("apps.payments.views.stripe.Webhook.construct_event")
    def test_refund_revokes_downloads(self, mock_construct):
        vendor = _vendor("v2@example.com", "Vendor Two")
        buyer = User.objects.create_user(email="buyer2@example.com", password="s3cure-pass-1")
        order, suborder, product_file = _paid_order_with_file(
            vendor, buyer, session_id="cs_test2", pi_id="pi_test2"
        )
        suborder.status = "paid"
        suborder.save(update_fields=["status"])
        DownloadGrant.objects.create(
            buyer=buyer, line_item=suborder.line_items.first(), product_file=product_file
        )
        mock_construct.return_value = _stripe_event(
            "evt_2", "charge.refunded", {"payment_intent": "pi_test2"}
        )

        response = self.client.post(
            "/api/webhooks/stripe/", data=b"{}", content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )

        self.assertEqual(response.status_code, 200)
        grant = DownloadGrant.objects.get(buyer=buyer, product_file=product_file)
        self.assertIsNotNone(grant.revoked_at)


class DownloadListViewTests(APITestCase):
    @patch("apps.delivery.services.generate_presigned_get")
    def test_buyer_can_list_their_downloads(self, mock_presign):
        mock_presign.return_value = "https://r2.example.com/signed"
        vendor = _vendor("v3@example.com", "Vendor Three")
        buyer = User.objects.create_user(email="buyer3@example.com", password="s3cure-pass-1")
        order, suborder, product_file = _paid_order_with_file(
            vendor, buyer, session_id="cs_test3", pi_id="pi_test3"
        )
        suborder.status = "paid"
        suborder.save(update_fields=["status"])
        DownloadGrant.objects.create(
            buyer=buyer, line_item=suborder.line_items.first(), product_file=product_file
        )
        self.client.force_authenticate(buyer)

        response = self.client.get(f"/api/orders/{order.id}/downloads/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(len(response.data[0]["files"]), 1)
        self.assertEqual(response.data[0]["files"][0]["download_url"], "https://r2.example.com/signed")

    def test_other_buyer_cannot_see_order(self):
        vendor = _vendor("v4@example.com", "Vendor Four")
        buyer = User.objects.create_user(email="buyer4@example.com", password="s3cure-pass-1")
        stranger = User.objects.create_user(email="stranger@example.com", password="s3cure-pass-1")
        order, suborder, product_file = _paid_order_with_file(
            vendor, buyer, session_id="cs_test4", pi_id="pi_test4"
        )
        suborder.status = "paid"
        suborder.save(update_fields=["status"])
        DownloadGrant.objects.create(
            buyer=buyer, line_item=suborder.line_items.first(), product_file=product_file
        )
        self.client.force_authenticate(stranger)

        response = self.client.get(f"/api/orders/{order.id}/downloads/")

        self.assertEqual(response.status_code, 404)

    def test_revoked_grant_leaves_item_with_no_files(self):
        from django.utils import timezone

        vendor = _vendor("v5@example.com", "Vendor Five")
        buyer = User.objects.create_user(email="buyer5@example.com", password="s3cure-pass-1")
        order, suborder, product_file = _paid_order_with_file(
            vendor, buyer, session_id="cs_test5", pi_id="pi_test5"
        )
        suborder.status = "refunded"
        suborder.save(update_fields=["status"])
        DownloadGrant.objects.create(
            buyer=buyer, line_item=suborder.line_items.first(), product_file=product_file,
            revoked_at=timezone.now(),
        )
        self.client.force_authenticate(buyer)

        response = self.client.get(f"/api/orders/{order.id}/downloads/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["status"], "refunded")
        self.assertEqual(response.data[0]["files"], [])

    def test_pending_suborder_is_not_shown(self):
        vendor = _vendor("v6@example.com", "Vendor Six")
        buyer = User.objects.create_user(email="buyer6@example.com", password="s3cure-pass-1")
        order, suborder, product_file = _paid_order_with_file(
            vendor, buyer, session_id="cs_test6", pi_id="pi_test6"
        )
        self.client.force_authenticate(buyer)

        response = self.client.get(f"/api/orders/{order.id}/downloads/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    @patch("apps.delivery.services.generate_presigned_get")
    def test_multi_vendor_order_shows_every_item_even_without_files(self, mock_presign):
        # Regression test: a buyer purchasing from two vendors in one order should see
        # BOTH line items on their order, even if one vendor never uploaded a file for
        # their product — not have it silently vanish because it has no DownloadGrant.
        mock_presign.return_value = "https://r2.example.com/signed"
        vendor_a = _vendor("va@example.com", "Vendor A")
        vendor_b = _vendor("vb@example.com", "Vendor B")
        buyer = User.objects.create_user(email="multibuyer@example.com", password="s3cure-pass-1")

        product_with_file = Product.objects.create(
            vendor=vendor_a, title="Has File", slug="has-file", description="",
            category="template", price_cents=1000,
        )
        product_file = ProductFile.objects.create(
            product=product_with_file, storage_key="products/a/files/1/asset.zip",
            original_filename="asset.zip", byte_size=10, content_type="application/zip",
        )
        product_without_file = Product.objects.create(
            vendor=vendor_b, title="No File Yet", slug="no-file-yet", description="",
            category="template", price_cents=2000,
        )

        order = Order.objects.create(buyer=buyer, total_cents=3000, currency="usd")
        suborder_a = VendorSuborder.objects.create(
            order=order, vendor=vendor_a, subtotal_cents=1000, platform_fee_cents=150,
            status="paid", stripe_checkout_session_id="cs_a", stripe_payment_intent_id="pi_a",
        )
        suborder_b = VendorSuborder.objects.create(
            order=order, vendor=vendor_b, subtotal_cents=2000, platform_fee_cents=300,
            status="paid", stripe_checkout_session_id="cs_b", stripe_payment_intent_id="pi_b",
        )
        line_item_a = OrderLineItem.objects.create(
            suborder=suborder_a, product=product_with_file, unit_price_cents=1000,
            product_title_snapshot=product_with_file.title,
        )
        OrderLineItem.objects.create(
            suborder=suborder_b, product=product_without_file, unit_price_cents=2000,
            product_title_snapshot=product_without_file.title,
        )
        DownloadGrant.objects.create(buyer=buyer, line_item=line_item_a, product_file=product_file)

        self.client.force_authenticate(buyer)
        response = self.client.get(f"/api/orders/{order.id}/downloads/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        titles = {item["product_title"]: item["files"] for item in response.data}
        self.assertEqual(len(titles["Has File"]), 1)
        self.assertEqual(titles["No File Yet"], [])
