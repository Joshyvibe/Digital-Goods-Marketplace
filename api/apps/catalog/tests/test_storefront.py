from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, VendorProfile
from apps.catalog.models import Product


def _vendor(email, store_name, **kwargs) -> VendorProfile:
    user = User.objects.create_user(email=email, password="s3cure-pass-1")
    return VendorProfile.objects.create(
        user=user, store_name=store_name, slug=store_name.lower().replace(" ", "-"), **kwargs
    )


class VendorStorefrontTests(APITestCase):
    def test_returns_store_name_and_published_products(self):
        vendor = _vendor("s1@example.com", "Story Shop", charges_enabled=True)
        Product.objects.create(
            vendor=vendor, title="Live", slug="live", description="d", category="template",
            price_cents=1000, status="published",
        )
        Product.objects.create(
            vendor=vendor, title="Draft", slug="draft", description="d", category="template",
            price_cents=1000, status="draft",
        )

        response = self.client.get("/api/store/story-shop/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["store_name"], "Story Shop")
        self.assertEqual(len(response.data["products"]), 1)
        self.assertEqual(response.data["products"][0]["title"], "Live")

    def test_unknown_slug_404s(self):
        response = self.client.get("/api/store/does-not-exist/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_vendor_not_yet_onboarded_shows_empty_product_list_not_404(self):
        vendor = _vendor("s2@example.com", "Pending Shop", charges_enabled=False)
        Product.objects.create(
            vendor=vendor, title="Hidden", slug="hidden", description="d", category="template",
            price_cents=1000, status="published",
        )

        response = self.client.get("/api/store/pending-shop/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["store_name"], "Pending Shop")
        self.assertEqual(response.data["products"], [])

    def test_no_internal_fields_leaked(self):
        vendor = _vendor(
            "s3@example.com", "Careful Shop", charges_enabled=True, stripe_account_id="acct_secret"
        )

        response = self.client.get("/api/store/careful-shop/")

        self.assertNotIn("stripe_account_id", response.data)
        self.assertNotIn("acct_secret", str(response.data))
        self.assertNotIn("charges_enabled", response.data)
