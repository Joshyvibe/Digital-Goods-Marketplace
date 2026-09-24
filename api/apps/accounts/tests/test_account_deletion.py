from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, VendorProfile
from apps.catalog.models import Product
from apps.orders.models import Order, OrderLineItem, VendorSuborder


def _login(client, email, password="s3cure-pass-1"):
    login = client.post("/api/auth/token/", {"email": email, "password": password})
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    return login.data["access"]


class AccountDeletionTests(APITestCase):
    def test_clean_buyer_account_is_hard_deleted(self):
        User.objects.create_user(email="clean@example.com", password="s3cure-pass-1")
        _login(self.client, "clean@example.com")

        response = self.client.delete("/api/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["outcome"], "deleted")
        self.assertFalse(User.objects.filter(email="clean@example.com").exists())

    def test_clean_vendor_with_no_sales_is_hard_deleted(self):
        user = User.objects.create_user(email="freshvendor@example.com", password="s3cure-pass-1")
        vendor = VendorProfile.objects.create(user=user, store_name="Fresh Vendor", slug="fresh-vendor")
        Product.objects.create(
            vendor=vendor, title="Unsold Thing", slug="unsold-thing", description="d",
            category="template", price_cents=1000, status="draft",
        )
        _login(self.client, "freshvendor@example.com")

        response = self.client.delete("/api/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["outcome"], "deleted")
        self.assertFalse(User.objects.filter(email="freshvendor@example.com").exists())
        self.assertFalse(VendorProfile.objects.filter(id=vendor.id).exists())
        self.assertFalse(Product.objects.filter(slug="unsold-thing").exists())

    def test_buyer_with_order_history_is_deactivated_not_deleted(self):
        user = User.objects.create_user(email="pastbuyer@example.com", password="s3cure-pass-1")
        Order.objects.create(buyer=user, total_cents=1000, currency="usd")
        _login(self.client, "pastbuyer@example.com")

        response = self.client.delete("/api/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["outcome"], "deactivated")

        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertNotEqual(user.email, "pastbuyer@example.com")
        self.assertFalse(user.has_usable_password())
        # The order itself must survive untouched.
        self.assertTrue(Order.objects.filter(buyer=user).exists())

    def test_vendor_with_sales_is_deactivated_and_products_archived(self):
        vendor_user = User.objects.create_user(email="sellingvendor@example.com", password="s3cure-pass-1")
        vendor = VendorProfile.objects.create(
            user=vendor_user, store_name="Selling Vendor", slug="selling-vendor", charges_enabled=True
        )
        product = Product.objects.create(
            vendor=vendor, title="Sold Thing", slug="sold-thing", description="d",
            category="template", price_cents=1000, status="published",
        )
        buyer = User.objects.create_user(email="somebuyer@example.com", password="s3cure-pass-1")
        order = Order.objects.create(buyer=buyer, total_cents=1000, currency="usd")
        suborder = VendorSuborder.objects.create(
            order=order, vendor=vendor, subtotal_cents=1000, platform_fee_cents=150
        )
        OrderLineItem.objects.create(
            suborder=suborder, product=product, unit_price_cents=1000, product_title_snapshot="Sold Thing"
        )

        _login(self.client, "sellingvendor@example.com")
        response = self.client.delete("/api/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["outcome"], "deactivated")

        vendor_user.refresh_from_db()
        self.assertFalse(vendor_user.is_active)
        product.refresh_from_db()
        self.assertEqual(product.status, "archived")
        # The sold product row itself must survive (PROTECT) — the buyer's download
        # access and the order's line items depend on it.
        self.assertTrue(Product.objects.filter(id=product.id).exists())

    def test_deactivated_account_cannot_authenticate_with_old_access_token(self):
        User.objects.create_user(email="soontoinactive@example.com", password="s3cure-pass-1")
        Order.objects.create(
            buyer=User.objects.get(email="soontoinactive@example.com"), total_cents=500, currency="usd"
        )
        access = _login(self.client, "soontoinactive@example.com")

        self.client.delete("/api/auth/me/")

        # Re-use the *same* access token that was valid moments ago — simplejwt's
        # JWTAuthentication checks is_active on every request, so this must now fail even
        # though the token itself hasn't expired.
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_requires_authentication(self):
        response = self.client.delete("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_deleting_does_not_break_a_second_user_with_the_same_deleted_placeholder(self):
        # Two different accounts soft-deleting must not collide on the anonymized email
        # (it's keyed by id, but worth locking in explicitly).
        u1 = User.objects.create_user(email="u1@example.com", password="s3cure-pass-1")
        Order.objects.create(buyer=u1, total_cents=100, currency="usd")
        u2 = User.objects.create_user(email="u2@example.com", password="s3cure-pass-1")
        Order.objects.create(buyer=u2, total_cents=100, currency="usd")

        _login(self.client, "u1@example.com")
        self.client.delete("/api/auth/me/")
        self.client.credentials()
        _login(self.client, "u2@example.com")
        response = self.client.delete("/api/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        u1.refresh_from_db()
        u2.refresh_from_db()
        self.assertNotEqual(u1.email, u2.email)
