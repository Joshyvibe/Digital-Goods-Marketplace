from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, VendorProfile
from apps.catalog.models import Product


def _vendor(email: str, charges_enabled: bool) -> VendorProfile:
    user = User.objects.create_user(email=email, password="s3cure-pass-1")
    return VendorProfile.objects.create(
        user=user,
        store_name=email.split("@")[0],
        slug=email.split("@")[0],
        charges_enabled=charges_enabled,
        payouts_enabled=charges_enabled,
    )


def _product(vendor: VendorProfile, status_: str, title: str = "Test Product") -> Product:
    return Product.objects.create(
        vendor=vendor,
        title=title,
        slug=title.lower().replace(" ", "-"),
        description="",
        category="template",
        price_cents=1000,
        status=status_,
    )


class PublicCatalogTests(APITestCase):
    def test_published_product_from_payable_vendor_is_listed(self):
        vendor = _vendor("payable@example.com", charges_enabled=True)
        _product(vendor, "published")

        response = self.client.get("/api/products/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_draft_product_is_excluded(self):
        vendor = _vendor("payable2@example.com", charges_enabled=True)
        _product(vendor, "draft")

        response = self.client.get("/api/products/")

        self.assertEqual(response.data["count"], 0)

    def test_archived_product_is_excluded(self):
        vendor = _vendor("payable3@example.com", charges_enabled=True)
        _product(vendor, "archived")

        response = self.client.get("/api/products/")

        self.assertEqual(response.data["count"], 0)

    def test_published_product_from_unpaid_out_vendor_is_excluded(self):
        # A vendor mid-onboarding (charges_enabled=False) can save a "published" product,
        # but it must not appear in the public catalog until Stripe confirms payability.
        vendor = _vendor("notyetpayable@example.com", charges_enabled=False)
        _product(vendor, "published")

        response = self.client.get("/api/products/")

        self.assertEqual(response.data["count"], 0)

    def test_public_serializer_never_exposes_stripe_account_id(self):
        vendor = _vendor("payable4@example.com", charges_enabled=True)
        vendor.stripe_account_id = "acct_secret123"
        vendor.save(update_fields=["stripe_account_id"])
        _product(vendor, "published")

        response = self.client.get("/api/products/")

        body = str(response.data)
        self.assertNotIn("acct_secret123", body)
        self.assertNotIn("stripe_account_id", body)

    def test_detail_lookup_by_slug(self):
        vendor = _vendor("payable5@example.com", charges_enabled=True)
        _product(vendor, "published", title="Unique Slug Product")

        response = self.client.get("/api/products/unique-slug-product/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Unique Slug Product")

    def test_detail_lookup_404s_for_draft_product(self):
        vendor = _vendor("payable6@example.com", charges_enabled=True)
        _product(vendor, "draft", title="Hidden Product")

        response = self.client.get("/api/products/hidden-product/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
