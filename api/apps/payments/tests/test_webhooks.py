from unittest.mock import patch

from rest_framework.test import APITestCase

from apps.accounts.models import User, VendorProfile
from apps.orders.models import Order, VendorSuborder
from apps.payments.models import StripeWebhookEvent
from apps.payments.stripe_client import stripe


def _vendor(email, store_name, **kwargs) -> VendorProfile:
    user = User.objects.create_user(email=email, password="s3cure-pass-1")
    defaults = {"charges_enabled": True, "payouts_enabled": True, "stripe_account_id": "acct_fake"}
    defaults.update(kwargs)
    return VendorProfile.objects.create(
        user=user, store_name=store_name, slug=store_name.lower().replace(" ", "-"), **defaults
    )


def _order_with_suborder(vendor, subtotal_cents=1000, session_id="cs_test1", pi_id="pi_test1", status_="pending"):
    buyer = User.objects.create_user(email=f"buyer{vendor.id}@example.com", password="s3cure-pass-1")
    order = Order.objects.create(buyer=buyer, total_cents=subtotal_cents, currency="usd")
    suborder = VendorSuborder.objects.create(
        order=order,
        vendor=vendor,
        subtotal_cents=subtotal_cents,
        platform_fee_cents=round(subtotal_cents * 0.15),
        status=status_,
        stripe_checkout_session_id=session_id,
        stripe_payment_intent_id=pi_id,
    )
    return order, suborder


def _stripe_event(event_id: str, event_type: str, obj: dict):
    return stripe.Event.construct_from(
        {"id": event_id, "type": event_type, "data": {"object": obj}}, "fake_api_key"
    )


class WebhookSignatureTests(APITestCase):
    @patch("apps.payments.views.stripe.Webhook.construct_event")
    def test_invalid_signature_returns_400(self, mock_construct):
        mock_construct.side_effect = ValueError("bad payload")

        response = self.client.post(
            "/api/webhooks/stripe/", data=b"{}", content_type="application/json",
            HTTP_STRIPE_SIGNATURE="bad-sig",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(StripeWebhookEvent.objects.count(), 0)

    @patch("apps.payments.views.stripe.Webhook.construct_event")
    def test_unhandled_event_type_is_marked_ignored(self, mock_construct):
        mock_construct.return_value = _stripe_event("evt_unhandled", "customer.created", {})

        response = self.client.post(
            "/api/webhooks/stripe/", data=b"{}", content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )

        self.assertEqual(response.status_code, 200)
        record = StripeWebhookEvent.objects.get(stripe_event_id="evt_unhandled")
        self.assertEqual(record.status, "ignored")


class WebhookIdempotencyTests(APITestCase):
    @patch("apps.payments.views.stripe.Webhook.construct_event")
    def test_replaying_same_event_id_is_a_no_op(self, mock_construct):
        vendor = _vendor("v1@example.com", "Vendor One")
        order, suborder = _order_with_suborder(vendor, session_id="cs_replay")
        event = _stripe_event(
            "evt_replay", "checkout.session.completed", {"id": "cs_replay", "payment_intent": "pi_test1"}
        )
        mock_construct.return_value = event

        first = self.client.post(
            "/api/webhooks/stripe/", data=b"{}", content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )
        suborder.refresh_from_db()
        first_paid_at = suborder.paid_at

        self.assertEqual(first.status_code, 200)
        self.assertEqual(suborder.status, "paid")
        self.assertIsNotNone(first_paid_at)
        self.assertEqual(StripeWebhookEvent.objects.filter(stripe_event_id="evt_replay").count(), 1)

        second = self.client.post(
            "/api/webhooks/stripe/", data=b"{}", content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )
        suborder.refresh_from_db()

        self.assertEqual(second.status_code, 200)
        self.assertEqual(suborder.paid_at, first_paid_at)  # untouched by the replay
        self.assertEqual(StripeWebhookEvent.objects.filter(stripe_event_id="evt_replay").count(), 1)


class CheckoutSessionCompletedTests(APITestCase):
    @patch("apps.payments.views.stripe.Webhook.construct_event")
    def test_marks_suborder_paid_and_order_paid_for_single_vendor_order(self, mock_construct):
        vendor = _vendor("v2@example.com", "Vendor Two")
        order, suborder = _order_with_suborder(vendor, session_id="cs_a")
        mock_construct.return_value = _stripe_event(
            "evt_a", "checkout.session.completed", {"id": "cs_a", "payment_intent": "pi_test1"}
        )

        response = self.client.post(
            "/api/webhooks/stripe/", data=b"{}", content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )

        self.assertEqual(response.status_code, 200)
        suborder.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(suborder.status, "paid")
        self.assertIsNotNone(suborder.paid_at)
        self.assertEqual(order.status, "paid")

    @patch("apps.payments.views.stripe.Webhook.construct_event")
    def test_multi_vendor_order_is_partially_paid_until_all_suborders_paid(self, mock_construct):
        vendor_a = _vendor("v3@example.com", "Vendor Three")
        vendor_b = _vendor("v4@example.com", "Vendor Four")
        buyer = User.objects.create_user(email="buyer99@example.com", password="s3cure-pass-1")
        order = Order.objects.create(buyer=buyer, total_cents=3000, currency="usd")
        suborder_a = VendorSuborder.objects.create(
            order=order, vendor=vendor_a, subtotal_cents=1000, platform_fee_cents=150,
            stripe_checkout_session_id="cs_multi_a", stripe_payment_intent_id="pi_multi_a",
        )
        VendorSuborder.objects.create(
            order=order, vendor=vendor_b, subtotal_cents=2000, platform_fee_cents=300,
            stripe_checkout_session_id="cs_multi_b", stripe_payment_intent_id="pi_multi_b",
        )

        mock_construct.return_value = _stripe_event(
            "evt_multi_a", "checkout.session.completed",
            {"id": "cs_multi_a", "payment_intent": "pi_multi_a"},
        )
        self.client.post(
            "/api/webhooks/stripe/", data=b"{}", content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )

        order.refresh_from_db()
        suborder_a.refresh_from_db()
        self.assertEqual(suborder_a.status, "paid")
        self.assertEqual(order.status, "partially_paid")

    @patch("apps.payments.views.stripe.Webhook.construct_event")
    def test_unknown_session_id_does_not_crash(self, mock_construct):
        mock_construct.return_value = _stripe_event(
            "evt_unknown", "checkout.session.completed",
            {"id": "cs_does_not_exist", "payment_intent": "pi_x"},
        )

        response = self.client.post(
            "/api/webhooks/stripe/", data=b"{}", content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(StripeWebhookEvent.objects.get(stripe_event_id="evt_unknown").status, "processed")


class PaymentFailedTests(APITestCase):
    @patch("apps.payments.views.stripe.Webhook.construct_event")
    def test_marks_suborder_failed(self, mock_construct):
        # Looked up via metadata.suborder_id, not stripe_payment_intent_id — a failed
        # payment can arrive before that field is ever back-filled (see
        # payment_intent_data.metadata in orders/services.py and the docstring on
        # handle_payment_failed for why).
        vendor = _vendor("v5@example.com", "Vendor Five")
        order, suborder = _order_with_suborder(vendor, pi_id="")
        mock_construct.return_value = _stripe_event(
            "evt_fail", "payment_intent.payment_failed",
            {"id": "pi_fail1", "metadata": {"suborder_id": str(suborder.id)}},
        )

        self.client.post(
            "/api/webhooks/stripe/", data=b"{}", content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )

        suborder.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(suborder.status, "failed")
        self.assertEqual(order.status, "failed")

    @patch("apps.payments.views.stripe.Webhook.construct_event")
    def test_missing_metadata_does_not_crash(self, mock_construct):
        mock_construct.return_value = _stripe_event(
            "evt_fail_nometa", "payment_intent.payment_failed", {"id": "pi_nometa", "metadata": {}}
        )

        response = self.client.post(
            "/api/webhooks/stripe/", data=b"{}", content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )

        self.assertEqual(response.status_code, 200)


class AccountUpdatedTests(APITestCase):
    @patch("apps.payments.views.stripe.Webhook.construct_event")
    def test_syncs_vendor_status_from_account_payload(self, mock_construct):
        vendor = _vendor(
            "v6@example.com", "Vendor Six",
            charges_enabled=False, payouts_enabled=False, stripe_account_id="acct_sync",
        )
        account_obj = {
            "id": "acct_sync",
            "charges_enabled": True,
            "payouts_enabled": True,
            "requirements": {"disabled_reason": None},
        }
        mock_construct.return_value = _stripe_event("evt_acct", "account.updated", account_obj)

        response = self.client.post(
            "/api/webhooks/stripe/", data=b"{}", content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )

        self.assertEqual(response.status_code, 200)
        vendor.refresh_from_db()
        self.assertTrue(vendor.charges_enabled)
        self.assertTrue(vendor.payouts_enabled)
        self.assertEqual(vendor.onboarding_status, "complete")

    @patch("apps.payments.views.stripe.Webhook.construct_event")
    def test_unknown_account_id_does_not_crash(self, mock_construct):
        account_obj = {
            "id": "acct_ghost",
            "charges_enabled": True,
            "payouts_enabled": True,
            "requirements": {"disabled_reason": None},
        }
        mock_construct.return_value = _stripe_event("evt_ghost", "account.updated", account_obj)

        response = self.client.post(
            "/api/webhooks/stripe/", data=b"{}", content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )

        self.assertEqual(response.status_code, 200)


class ChargeRefundedTests(APITestCase):
    @patch("apps.payments.views.stripe.Webhook.construct_event")
    def test_marks_suborder_refunded(self, mock_construct):
        vendor = _vendor("v7@example.com", "Vendor Seven")
        order, suborder = _order_with_suborder(vendor, pi_id="pi_refund1", status_="paid")
        mock_construct.return_value = _stripe_event(
            "evt_refund", "charge.refunded", {"payment_intent": "pi_refund1"}
        )

        response = self.client.post(
            "/api/webhooks/stripe/", data=b"{}", content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )

        self.assertEqual(response.status_code, 200)
        suborder.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(suborder.status, "refunded")
        self.assertEqual(order.status, "refunded")

    @patch("apps.payments.views.stripe.Webhook.construct_event")
    def test_missing_payment_intent_on_charge_does_not_crash(self, mock_construct):
        mock_construct.return_value = _stripe_event("evt_no_pi", "charge.refunded", {})

        response = self.client.post(
            "/api/webhooks/stripe/", data=b"{}", content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )

        self.assertEqual(response.status_code, 200)


def _raise_boom(event):
    raise RuntimeError("boom")


class WebhookHandlerFailureTests(APITestCase):
    # HANDLERS is built once at module import time as {event_type: <function ref>}, so
    # patching apps.payments.services.handle_checkout_completed wouldn't touch the
    # reference already captured in that dict — patch the dict itself, where the view
    # actually looks handlers up.
    @patch("apps.payments.views.HANDLERS", {"checkout.session.completed": _raise_boom})
    @patch("apps.payments.views.stripe.Webhook.construct_event")
    def test_handler_exception_marks_event_failed_and_returns_500(self, mock_construct):
        mock_construct.return_value = _stripe_event(
            "evt_boom", "checkout.session.completed", {"id": "cs_x", "payment_intent": "pi_x"}
        )

        # The view deliberately re-raises so Django (and Stripe's retry schedule) treats
        # this as a real 500 — tell the test client not to re-raise it for us, or this test
        # would fail with the raw RuntimeError instead of asserting the response.
        self.client.raise_request_exception = False
        response = self.client.post(
            "/api/webhooks/stripe/", data=b"{}", content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )

        self.assertEqual(response.status_code, 500)
        record = StripeWebhookEvent.objects.get(stripe_event_id="evt_boom")
        self.assertEqual(record.status, "failed")
        self.assertIn("boom", record.error_message)
