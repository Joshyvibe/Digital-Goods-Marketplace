from unittest.mock import MagicMock, patch

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, VendorProfile
from apps.payments.stripe_client import stripe


def _stripe_account(charges_enabled=False, payouts_enabled=False, disabled_reason=None):
    # Built via Account.construct_from, not a plain dict — a real stripe.Account wraps
    # nested fields (like .requirements) in StripeObjects with different attribute/dict
    # semantics than a plain dict. A plain-dict mock here would pass while the real SDK
    # response breaks the code it's supposed to be testing (see apply_stripe_account_snapshot).
    return stripe.Account.construct_from(
        {
            "id": "acct_fake123",
            "charges_enabled": charges_enabled,
            "payouts_enabled": payouts_enabled,
            "requirements": {"disabled_reason": disabled_reason},
        },
        "fake_api_key",
    )


class VendorOnboardingTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="vendor@example.com", password="s3cure-pass-1")
        login = self.client.post(
            "/api/auth/token/", {"email": "vendor@example.com", "password": "s3cure-pass-1"}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    @patch("apps.accounts.vendor_services.stripe.AccountLink.create")
    @patch("apps.accounts.vendor_services.stripe.Account.create")
    def test_onboard_creates_vendor_profile_and_stripe_account(self, mock_account_create, mock_link_create):
        mock_account_create.return_value = MagicMock(id="acct_fake123")
        mock_link_create.return_value = MagicMock(url="https://connect.stripe.com/setup/fake")

        response = self.client.post("/api/vendors/onboard/", {"store_name": "Studio North"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["onboarding_url"], "https://connect.stripe.com/setup/fake")

        vendor = VendorProfile.objects.get(user=self.user)
        self.assertEqual(vendor.stripe_account_id, "acct_fake123")
        self.assertEqual(vendor.onboarding_status, "pending")
        self.assertEqual(vendor.store_name, "Studio North")
        self.assertEqual(vendor.slug, "studio-north")

    @patch("apps.accounts.vendor_services.stripe.AccountLink.create")
    @patch("apps.accounts.vendor_services.stripe.Account.create")
    def test_onboard_reuses_existing_stripe_account_on_second_call(
        self, mock_account_create, mock_link_create
    ):
        mock_account_create.return_value = MagicMock(id="acct_fake123")
        mock_link_create.return_value = MagicMock(url="https://connect.stripe.com/setup/fake")

        self.client.post("/api/vendors/onboard/", {"store_name": "Studio North"})
        self.client.post("/api/vendors/onboard/", {"store_name": "Studio North"})

        self.assertEqual(mock_account_create.call_count, 1)  # not called again
        self.assertEqual(mock_link_create.call_count, 2)  # a fresh link every time
        self.assertEqual(VendorProfile.objects.filter(user=self.user).count(), 1)

    def test_onboard_requires_store_name(self):
        response = self.client.post("/api/vendors/onboard/", {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_onboard_requires_authentication(self):
        self.client.credentials()
        response = self.client.post("/api/vendors/onboard/", {"store_name": "Studio North"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_slug_collision_gets_suffixed(self):
        # A different store_name (store_name itself is globally unique) that slugifies to
        # the same value — punctuation aside, "Studio North!" and "Studio North" collide.
        other_user = User.objects.create_user(email="other@example.com", password="s3cure-pass-1")
        VendorProfile.objects.create(user=other_user, store_name="Studio North", slug="studio-north")

        with (
            patch("apps.accounts.vendor_services.stripe.Account.create") as mock_create,
            patch("apps.accounts.vendor_services.stripe.AccountLink.create") as mock_link,
        ):
            mock_create.return_value = MagicMock(id="acct_fake456")
            mock_link.return_value = MagicMock(url="https://connect.stripe.com/setup/fake")
            self.client.post("/api/vendors/onboard/", {"store_name": "Studio North!"})

        vendor = VendorProfile.objects.get(user=self.user)
        self.assertEqual(vendor.slug, "studio-north-2")

    def test_onboarding_status_syncs_from_stripe_and_flips_to_complete(self):
        vendor = VendorProfile.objects.create(
            user=self.user, store_name="Studio North", slug="studio-north", stripe_account_id="acct_fake123"
        )

        with patch("apps.accounts.vendor_services.stripe.Account.retrieve") as mock_retrieve:
            mock_retrieve.return_value = _stripe_account(charges_enabled=True, payouts_enabled=True)
            response = self.client.get("/api/vendors/onboarding-status/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["onboarding_status"], "complete")
        self.assertTrue(response.data["is_onboarded"])

        vendor.refresh_from_db()
        self.assertTrue(vendor.charges_enabled)
        self.assertTrue(vendor.payouts_enabled)

    def test_onboarding_status_flips_to_restricted_on_disabled_reason(self):
        VendorProfile.objects.create(
            user=self.user, store_name="Studio North", slug="studio-north", stripe_account_id="acct_fake123"
        )

        with patch("apps.accounts.vendor_services.stripe.Account.retrieve") as mock_retrieve:
            mock_retrieve.return_value = _stripe_account(disabled_reason="requirements.past_due")
            response = self.client.get("/api/vendors/onboarding-status/")

        self.assertEqual(response.data["onboarding_status"], "restricted")

    def test_onboarding_status_404s_for_non_vendor(self):
        response = self.client.get("/api/vendors/onboarding-status/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_onboarding_status_never_exposes_stripe_account_id(self):
        VendorProfile.objects.create(
            user=self.user, store_name="Studio North", slug="studio-north", stripe_account_id="acct_secret"
        )

        with patch("apps.accounts.vendor_services.stripe.Account.retrieve") as mock_retrieve:
            mock_retrieve.return_value = _stripe_account()
            response = self.client.get("/api/vendors/onboarding-status/")

        self.assertNotIn("stripe_account_id", response.data)
        self.assertNotIn("acct_secret", str(response.data))
