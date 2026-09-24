from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, VendorProfile


class VendorProfileUpdateTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="vendor@example.com", password="s3cure-pass-1")
        self.vendor = VendorProfile.objects.create(
            user=self.user, store_name="Old Name", slug="old-name", charges_enabled=True
        )
        login = self.client.post(
            "/api/auth/token/", {"email": "vendor@example.com", "password": "s3cure-pass-1"}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_vendor_can_rename_store(self):
        response = self.client.patch("/api/vendors/onboarding-status/", {"store_name": "New Name"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["store_name"], "New Name")
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.store_name, "New Name")

    def test_rename_does_not_change_slug(self):
        self.client.patch("/api/vendors/onboarding-status/", {"store_name": "New Name"})

        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.slug, "old-name")  # stable — bookmarked URLs stay valid

    def test_cannot_rename_to_an_existing_store_name(self):
        other_user = User.objects.create_user(email="other@example.com", password="s3cure-pass-1")
        VendorProfile.objects.create(user=other_user, store_name="Taken Name", slug="taken-name")

        response = self.client.patch("/api/vendors/onboarding-status/", {"store_name": "Taken Name"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.store_name, "Old Name")

    def test_cannot_write_protected_fields_via_this_endpoint(self):
        response = self.client.patch(
            "/api/vendors/onboarding-status/",
            {"store_name": "New Name", "charges_enabled": False, "onboarding_status": "restricted"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.vendor.refresh_from_db()
        self.assertTrue(self.vendor.charges_enabled)  # untouched despite the attempt

    def test_non_vendor_gets_404(self):
        other_user = User.objects.create_user(email="buyer@example.com", password="s3cure-pass-1")
        login = self.client.post(
            "/api/auth/token/", {"email": "buyer@example.com", "password": "s3cure-pass-1"}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        response = self.client.patch("/api/vendors/onboarding-status/", {"store_name": "New Name"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_requires_authentication(self):
        self.client.credentials()
        response = self.client.patch("/api/vendors/onboarding-status/", {"store_name": "New Name"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
