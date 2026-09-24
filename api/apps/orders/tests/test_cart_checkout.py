from unittest.mock import MagicMock, patch

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, VendorProfile
from apps.catalog.models import Product
from apps.orders.models import CartItem, Order
from apps.payments.stripe_client import stripe
from apps.orders.services import (
    CheckoutError,
    add_item_to_cart,
    checkout_cart,
    create_checkout_sessions,
    create_order_from_cart,
    get_or_create_open_cart,
)


def _vendor(email: str, store_name: str, charges_enabled=True) -> VendorProfile:
    user = User.objects.create_user(email=email, password="s3cure-pass-1")
    return VendorProfile.objects.create(
        user=user,
        store_name=store_name,
        slug=store_name.lower().replace(" ", "-"),
        charges_enabled=charges_enabled,
        payouts_enabled=charges_enabled,
        stripe_account_id="acct_fake" if charges_enabled else "",
    )


def _product(vendor, title, price_cents, status_="published") -> Product:
    return Product.objects.create(
        vendor=vendor,
        title=title,
        slug=title.lower().replace(" ", "-"),
        description="d",
        category="template",
        price_cents=price_cents,
        status=status_,
    )


class CartServiceTests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(email="buyer@example.com", password="s3cure-pass-1")
        self.vendor = _vendor("vendor@example.com", "Studio North")
        self.product = _product(self.vendor, "Template A", 2000)

    def test_get_or_create_open_cart_is_idempotent(self):
        cart1 = get_or_create_open_cart(self.buyer)
        cart2 = get_or_create_open_cart(self.buyer)
        self.assertEqual(cart1.id, cart2.id)

    def test_cannot_add_unpublished_product(self):
        draft_product = _product(self.vendor, "Draft Thing", 1000, status_="draft")
        cart = get_or_create_open_cart(self.buyer)
        with self.assertRaises(Exception):
            add_item_to_cart(cart, draft_product)

    def test_cannot_add_product_from_unpaid_out_vendor(self):
        unpaid_vendor = _vendor("unpaid@example.com", "Unpaid Store", charges_enabled=False)
        product = _product(unpaid_vendor, "Thing", 1000)
        cart = get_or_create_open_cart(self.buyer)
        with self.assertRaises(Exception):
            add_item_to_cart(cart, product)

    def test_adding_same_product_twice_is_a_no_op(self):
        cart = get_or_create_open_cart(self.buyer)
        add_item_to_cart(cart, self.product)
        add_item_to_cart(cart, self.product)
        self.assertEqual(CartItem.objects.filter(cart=cart).count(), 1)


class CreateOrderFromCartTests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(email="buyer@example.com", password="s3cure-pass-1")

    def test_empty_cart_raises(self):
        cart = get_or_create_open_cart(self.buyer)
        with self.assertRaises(CheckoutError):
            create_order_from_cart(cart)

    def test_single_vendor_cart_creates_one_suborder(self):
        vendor = _vendor("v1@example.com", "Vendor One")
        product = _product(vendor, "Thing", 2000)
        cart = get_or_create_open_cart(self.buyer)
        add_item_to_cart(cart, product)

        order = create_order_from_cart(cart)

        self.assertEqual(order.total_cents, 2000)
        self.assertEqual(order.suborders.count(), 1)
        suborder = order.suborders.get()
        self.assertEqual(suborder.vendor, vendor)
        self.assertEqual(suborder.subtotal_cents, 2000)
        self.assertEqual(suborder.platform_fee_cents, round(2000 * 0.15))  # = 300
        self.assertEqual(suborder.line_items.count(), 1)

    def test_multi_vendor_cart_creates_one_suborder_per_vendor_with_correct_split(self):
        vendor_a = _vendor("va@example.com", "Vendor A")
        vendor_b = _vendor("vb@example.com", "Vendor B")
        product_a1 = _product(vendor_a, "A1", 1000)
        product_a2 = _product(vendor_a, "A2", 1500)
        product_b1 = _product(vendor_b, "B1", 3000)

        cart = get_or_create_open_cart(self.buyer)
        for p in (product_a1, product_a2, product_b1):
            add_item_to_cart(cart, p)

        order = create_order_from_cart(cart)

        self.assertEqual(order.total_cents, 1000 + 1500 + 3000)
        self.assertEqual(order.suborders.count(), 2)

        suborder_a = order.suborders.get(vendor=vendor_a)
        self.assertEqual(suborder_a.subtotal_cents, 2500)
        self.assertEqual(suborder_a.platform_fee_cents, round(2500 * 0.15))
        self.assertEqual(suborder_a.line_items.count(), 2)

        suborder_b = order.suborders.get(vendor=vendor_b)
        self.assertEqual(suborder_b.subtotal_cents, 3000)
        self.assertEqual(suborder_b.platform_fee_cents, round(3000 * 0.15))
        self.assertEqual(suborder_b.line_items.count(), 1)

        # No cross-contamination between vendors' line items.
        self.assertEqual(
            {li.product_title_snapshot for li in suborder_a.line_items.all()}, {"A1", "A2"}
        )
        self.assertEqual({li.product_title_snapshot for li in suborder_b.line_items.all()}, {"B1"})

    def test_cart_marked_converted_after_order_creation(self):
        vendor = _vendor("v2@example.com", "Vendor Two")
        product = _product(vendor, "Thing", 1000)
        cart = get_or_create_open_cart(self.buyer)
        add_item_to_cart(cart, product)

        create_order_from_cart(cart)

        cart.refresh_from_db()
        self.assertEqual(cart.status, "converted")

    def test_next_cart_lookup_creates_a_fresh_open_cart_after_conversion(self):
        vendor = _vendor("v3@example.com", "Vendor Three")
        product = _product(vendor, "Thing", 1000)
        cart = get_or_create_open_cart(self.buyer)
        add_item_to_cart(cart, product)
        create_order_from_cart(cart)

        new_cart = get_or_create_open_cart(self.buyer)

        self.assertNotEqual(new_cart.id, cart.id)
        self.assertEqual(new_cart.items.count(), 0)

    def test_product_unpublished_after_adding_to_cart_blocks_checkout(self):
        vendor = _vendor("v4@example.com", "Vendor Four")
        product = _product(vendor, "Thing", 1000)
        cart = get_or_create_open_cart(self.buyer)
        add_item_to_cart(cart, product)

        product.status = "archived"
        product.save(update_fields=["status"])

        with self.assertRaises(CheckoutError):
            create_order_from_cart(cart)

    def test_order_total_never_trusts_a_client_value_only_server_computed_prices(self):
        # Sanity check that total/fees are derived purely from Product.price_cents at
        # checkout time, not from anything the request could have supplied.
        vendor = _vendor("v5@example.com", "Vendor Five")
        product = _product(vendor, "Thing", 999)
        cart = get_or_create_open_cart(self.buyer)
        add_item_to_cart(cart, product)

        order = create_order_from_cart(cart)

        self.assertEqual(order.total_cents, 999)
        self.assertEqual(order.suborders.get().platform_fee_cents, round(999 * 0.15))


class CreateCheckoutSessionsTests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(email="buyer@example.com", password="s3cure-pass-1")

    @patch("apps.orders.services.stripe.checkout.Session.create")
    def test_creates_one_session_per_suborder_with_correct_split_params(self, mock_create):
        vendor_a = _vendor("va2@example.com", "Vendor A2")
        vendor_b = _vendor("vb2@example.com", "Vendor B2")
        _product_a = _product(vendor_a, "A", 1000)
        _product_b = _product(vendor_b, "B", 2000)

        cart = get_or_create_open_cart(self.buyer)
        add_item_to_cart(cart, _product_a)
        add_item_to_cart(cart, _product_b)
        order = create_order_from_cart(cart)

        # payment_intent=None matches reality (confirmed live): Stripe doesn't create the
        # PaymentIntent until the buyer actually reaches payment, not at Session.create().
        mock_create.side_effect = [
            MagicMock(id="cs_a", url="https://checkout.stripe.com/a", payment_intent=None),
            MagicMock(id="cs_b", url="https://checkout.stripe.com/b", payment_intent=None),
        ]

        urls = create_checkout_sessions(order)

        self.assertEqual(set(urls), {"https://checkout.stripe.com/a", "https://checkout.stripe.com/b"})
        self.assertEqual(mock_create.call_count, 2)

        suborder_a = order.suborders.get(vendor=vendor_a)
        suborder_b = order.suborders.get(vendor=vendor_b)

        for call in mock_create.call_args_list:
            kwargs = call.kwargs
            self.assertEqual(kwargs["mode"], "payment")
            self.assertEqual(len(kwargs["line_items"]), 1)  # each session only its vendor's items
            dest = kwargs["payment_intent_data"]["transfer_data"]["destination"]
            self.assertIn(dest, {vendor_a.stripe_account_id, vendor_b.stripe_account_id})
            # The suborder_id correlator that lets payment_intent.payment_failed find this
            # suborder even though no PaymentIntent exists yet at this point.
            metadata_suborder_id = kwargs["payment_intent_data"]["metadata"]["suborder_id"]
            self.assertIn(int(metadata_suborder_id), {suborder_a.id, suborder_b.id})

        suborder_a.refresh_from_db()
        self.assertEqual(suborder_a.stripe_checkout_session_id, "cs_a")
        # Not back-filled yet — only checkout.session.completed sets this (see payments/services.py).
        self.assertEqual(suborder_a.stripe_payment_intent_id, "")

    @patch("apps.orders.services.stripe.checkout.Session.create")
    def test_application_fee_amount_matches_suborder_platform_fee(self, mock_create):
        vendor = _vendor("v6@example.com", "Vendor Six")
        product = _product(vendor, "Thing", 10000)
        cart = get_or_create_open_cart(self.buyer)
        add_item_to_cart(cart, product)
        order = create_order_from_cart(cart)
        suborder = order.suborders.get()

        mock_create.return_value = MagicMock(id="cs_1", url="https://checkout.stripe.com/1", payment_intent="pi_1")

        create_checkout_sessions(order)

        fee_sent = mock_create.call_args.kwargs["payment_intent_data"]["application_fee_amount"]
        self.assertEqual(fee_sent, suborder.platform_fee_cents)
        self.assertEqual(fee_sent, round(10000 * 0.15))


class CheckoutApiTests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(email="buyer@example.com", password="s3cure-pass-1")
        login = self.client.post(
            "/api/auth/token/", {"email": "buyer@example.com", "password": "s3cure-pass-1"}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_checkout_requires_authentication(self):
        self.client.credentials()
        response = self.client.post("/api/orders/checkout/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_checkout_with_empty_cart_returns_400(self):
        response = self.client.post("/api/orders/checkout/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.orders.services.stripe.checkout.Session.create")
    def test_add_to_cart_then_checkout_returns_checkout_urls(self, mock_create):
        vendor = _vendor("v7@example.com", "Vendor Seven")
        product = _product(vendor, "Thing", 1500)

        add_response = self.client.post("/api/cart/items/", {"product_id": product.id})
        self.assertEqual(add_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(add_response.data["total_cents"], 1500)

        mock_create.return_value = MagicMock(
            id="cs_1", url="https://checkout.stripe.com/1", payment_intent="pi_1"
        )
        response = self.client.post("/api/orders/checkout/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["checkout_urls"], ["https://checkout.stripe.com/1"])
        self.assertTrue(Order.objects.filter(id=response.data["order_id"], buyer=self.buyer).exists())

    def test_remove_item_from_cart(self):
        vendor = _vendor("v8@example.com", "Vendor Eight")
        product = _product(vendor, "Thing", 1500)
        self.client.post("/api/cart/items/", {"product_id": product.id})

        response = self.client.delete(f"/api/cart/items/{product.id}/")

        self.assertEqual(response.data["items"], [])

    def test_cannot_view_another_buyers_order(self):
        other_buyer = User.objects.create_user(email="other@example.com", password="s3cure-pass-1")
        order = Order.objects.create(buyer=other_buyer, total_cents=1000, currency="usd")

        response = self.client.get(f"/api/orders/{order.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CheckoutCartRollbackTests(APITestCase):
    # Caught via live testing: a Stripe session-creation failure after the order was
    # already created must not leave the buyer's cart silently "converted" with an
    # abandoned, unpayable order behind it — see checkout_cart()'s docstring.
    def setUp(self):
        self.buyer = User.objects.create_user(email="buyer@example.com", password="s3cure-pass-1")

    @patch("apps.orders.services.stripe.checkout.Session.create")
    def test_stripe_failure_reopens_cart_and_deletes_the_order(self, mock_create):
        vendor = _vendor("v9@example.com", "Vendor Nine")
        product = _product(vendor, "Thing", 1000)
        cart = get_or_create_open_cart(self.buyer)
        add_item_to_cart(cart, product)

        mock_create.side_effect = Exception("boom")

        with self.assertRaises(Exception):
            checkout_cart(cart)

        cart.refresh_from_db()
        self.assertEqual(cart.status, "open")
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(Order.objects.filter(buyer=self.buyer).count(), 0)

    @patch("apps.orders.services.stripe.checkout.Session.create")
    def test_checkout_api_failure_lets_buyer_retry_with_same_cart(self, mock_create):
        vendor = _vendor("v10@example.com", "Vendor Ten")
        product = _product(vendor, "Thing", 1000)
        login = self.client.post(
            "/api/auth/token/", {"email": "buyer@example.com", "password": "s3cure-pass-1"}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        self.client.post("/api/cart/items/", {"product_id": product.id})

        # A real stripe.StripeError, not a generic Exception — this is what actually
        # reaches the view (create_checkout_sessions wraps it as CheckoutError, which is
        # what CheckoutView.post catches and turns into a clean 400).
        mock_create.side_effect = stripe.StripeError("boom")
        first = self.client.post("/api/orders/checkout/")
        self.assertEqual(first.status_code, status.HTTP_400_BAD_REQUEST)

        # The cart the buyer sees is still there, not silently emptied.
        cart_response = self.client.get("/api/cart/")
        self.assertEqual(cart_response.data["items"][0]["title"], "Thing")

        # And a real retry, once Stripe cooperates, works against that same cart.
        mock_create.side_effect = None
        mock_create.return_value = MagicMock(
            id="cs_retry", url="https://checkout.stripe.com/retry", payment_intent="pi_retry"
        )
        second = self.client.post("/api/orders/checkout/")
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data["checkout_urls"], ["https://checkout.stripe.com/retry"])
