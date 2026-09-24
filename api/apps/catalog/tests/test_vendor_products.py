from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, VendorProfile
from apps.catalog.models import Product, ProductFile


class VendorProductTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="vendor@example.com", password="s3cure-pass-1")
        self.vendor = VendorProfile.objects.create(
            user=self.user, store_name="Studio North", slug="studio-north", charges_enabled=True
        )
        login = self.client.post(
            "/api/auth/token/", {"email": "vendor@example.com", "password": "s3cure-pass-1"}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_non_vendor_cannot_access_vendor_product_endpoints(self):
        other = User.objects.create_user(email="buyer@example.com", password="s3cure-pass-1")
        login = self.client.post(
            "/api/auth/token/", {"email": "buyer@example.com", "password": "s3cure-pass-1"}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        response = self.client.get("/api/vendors/products/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_vendor_can_create_product_as_draft(self):
        response = self.client.post(
            "/api/vendors/products/",
            {
                "title": "My Template",
                "description": "A nice template",
                "category": "template",
                "price_cents": 2900,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "draft")
        self.assertEqual(response.data["slug"], "my-template")

        product = Product.objects.get(vendor=self.vendor)
        self.assertEqual(product.title, "My Template")

    def test_slug_unique_per_vendor_on_title_collision(self):
        self.client.post(
            "/api/vendors/products/",
            {"title": "My Template", "description": "A description.", "category": "template", "price_cents": 1000},
        )
        response = self.client.post(
            "/api/vendors/products/",
            {"title": "My Template", "description": "A description.", "category": "template", "price_cents": 1000},
        )

        self.assertEqual(response.data["slug"], "my-template-2")

    def test_vendor_only_sees_own_products(self):
        other_user = User.objects.create_user(email="other@example.com", password="s3cure-pass-1")
        other_vendor = VendorProfile.objects.create(
            user=other_user, store_name="Other Store", slug="other-store", charges_enabled=True
        )
        Product.objects.create(
            vendor=other_vendor, title="Not Mine", slug="not-mine", description="",
            category="template", price_cents=1000,
        )
        Product.objects.create(
            vendor=self.vendor, title="Mine", slug="mine", description="",
            category="template", price_cents=1000,
        )

        response = self.client.get("/api/vendors/products/")

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "Mine")

    def test_cannot_publish_before_stripe_onboarding_complete(self):
        self.vendor.charges_enabled = False
        self.vendor.save(update_fields=["charges_enabled"])

        response = self.client.post(
            "/api/vendors/products/",
            {
                "title": "My Template",
                "description": "A description.",
                "category": "template",
                "price_cents": 1000,
                "status": "published",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)

    def test_can_publish_once_onboarded(self):
        product = Product.objects.create(
            vendor=self.vendor, title="Mine", slug="mine", description="",
            category="template", price_cents=1000, status="draft",
        )

        response = self.client.patch(f"/api/vendors/products/{product.id}/", {"status": "published"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        product.refresh_from_db()
        self.assertEqual(product.status, "published")

    def test_vendor_cannot_edit_another_vendors_product(self):
        other_user = User.objects.create_user(email="other2@example.com", password="s3cure-pass-1")
        other_vendor = VendorProfile.objects.create(
            user=other_user, store_name="Other Store 2", slug="other-store-2", charges_enabled=True
        )
        product = Product.objects.create(
            vendor=other_vendor, title="Not Mine", slug="not-mine-2", description="",
            category="template", price_cents=1000,
        )

        response = self.client.patch(f"/api/vendors/products/{product.id}/", {"title": "Hijacked"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("apps.catalog.views.generate_presigned_put")
    def test_presign_upload_returns_url_and_storage_key(self, mock_presign):
        mock_presign.return_value = "https://r2.example.com/fake-upload-url"
        product = Product.objects.create(
            vendor=self.vendor, title="Mine", slug="mine", description="",
            category="template", price_cents=1000,
        )

        response = self.client.post(
            f"/api/vendors/products/{product.id}/presign-upload/",
            {"filename": "asset.zip", "content_type": "application/zip"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["upload_url"], "https://r2.example.com/fake-upload-url")
        self.assertTrue(response.data["storage_key"].startswith(f"products/{product.id}/files/"))
        self.assertTrue(response.data["storage_key"].endswith("/asset.zip"))

    @patch("apps.catalog.views.generate_presigned_put")
    def test_presign_upload_502s_when_r2_not_configured(self, mock_presign):
        from apps.delivery.r2_client import R2NotConfiguredError

        mock_presign.side_effect = R2NotConfiguredError()
        product = Product.objects.create(
            vendor=self.vendor, title="Mine", slug="mine", description="",
            category="template", price_cents=1000,
        )

        response = self.client.post(
            f"/api/vendors/products/{product.id}/presign-upload/",
            {"filename": "asset.zip", "content_type": "application/zip"},
        )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)

    def test_register_uploaded_file_creates_product_file(self):
        product = Product.objects.create(
            vendor=self.vendor, title="Mine", slug="mine", description="",
            category="template", price_cents=1000,
        )

        response = self.client.post(
            f"/api/vendors/products/{product.id}/files/",
            {
                "storage_key": f"products/{product.id}/files/abc123/asset.zip",
                "original_filename": "asset.zip",
                "byte_size": 12345,
                "content_type": "application/zip",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("storage_key", response.data)  # internal detail, never returned
        self.assertEqual(ProductFile.objects.get(product=product).original_filename, "asset.zip")

    def test_register_file_for_another_vendors_product_404s(self):
        other_user = User.objects.create_user(email="other3@example.com", password="s3cure-pass-1")
        other_vendor = VendorProfile.objects.create(
            user=other_user, store_name="Other Store 3", slug="other-store-3", charges_enabled=True
        )
        product = Product.objects.create(
            vendor=other_vendor, title="Not Mine", slug="not-mine-3", description="",
            category="template", price_cents=1000,
        )

        response = self.client.post(
            f"/api/vendors/products/{product.id}/files/",
            {
                "storage_key": "products/x/files/y/asset.zip",
                "original_filename": "asset.zip",
                "byte_size": 100,
                "content_type": "application/zip",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_file(self):
        product = Product.objects.create(
            vendor=self.vendor, title="Mine", slug="mine", description="",
            category="template", price_cents=1000,
        )
        product_file = ProductFile.objects.create(
            product=product, storage_key="k", original_filename="a.zip",
            byte_size=1, content_type="application/zip",
        )

        response = self.client.delete(f"/api/vendors/products/{product.id}/files/{product_file.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ProductFile.objects.filter(id=product_file.id).exists())
