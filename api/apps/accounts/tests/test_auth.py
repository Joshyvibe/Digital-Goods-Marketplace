from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from django.conf import settings

from apps.accounts.models import AuthProvider, User

REFRESH_COOKIE = settings.REFRESH_TOKEN_COOKIE_NAME


def _google_payload(**overrides):
    payload = {
        "sub": "google-user-123",
        "email": "buyer@example.com",
        "email_verified": True,
        "given_name": "Buyer",
    }
    payload.update(overrides)
    return payload


class RegisterAndLoginTests(APITestCase):
    def test_register_creates_user_and_sets_refresh_cookie(self):
        response = self.client.post(
            "/api/auth/register/", {"email": "new@example.com", "password": "s3cure-pass-1"}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["user"]["email"], "new@example.com")
        self.assertIn(REFRESH_COOKIE, response.cookies)
        self.assertTrue(response.cookies[REFRESH_COOKIE]["httponly"])
        self.assertTrue(User.objects.filter(email="new@example.com").exists())

    def test_login_with_valid_credentials(self):
        User.objects.create_user(email="buyer@example.com", password="s3cure-pass-1")

        response = self.client.post(
            "/api/auth/token/", {"email": "buyer@example.com", "password": "s3cure-pass-1"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertNotIn("refresh", response.data)  # refresh must never appear in the body
        self.assertIn(REFRESH_COOKIE, response.cookies)

    def test_wrong_password_for_existing_account_gets_accurate_message(self):
        # simplejwt's stock message ("No active account found with the given credentials")
        # is misleading here — the account *does* exist, only the password is wrong.
        User.objects.create_user(email="buyer@example.com", password="s3cure-pass-1")

        response = self.client.post(
            "/api/auth/token/", {"email": "buyer@example.com", "password": "wrong-password"}
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "Invalid email or password.")

    def test_nonexistent_email_gets_the_same_generic_message(self):
        # Same wording as the wrong-password case above — deliberately, so the response
        # never reveals whether an email is registered (no user-enumeration leak).
        response = self.client.post(
            "/api/auth/token/", {"email": "nobody@example.com", "password": "whatever-1"}
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "Invalid email or password.")

    def test_refresh_requires_cookie(self):
        response = self.client.post("/api/auth/token/refresh/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_clears_cookie(self):
        User.objects.create_user(email="buyer@example.com", password="s3cure-pass-1")
        login = self.client.post(
            "/api/auth/token/", {"email": "buyer@example.com", "password": "s3cure-pass-1"}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        response = self.client.post("/api/auth/logout/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.cookies[REFRESH_COOKIE].value, "")


class GoogleAuthTests(APITestCase):
    @patch("apps.accounts.services.google_id_token.verify_oauth2_token")
    def test_creates_new_user_on_first_google_sign_in(self, mock_verify):
        mock_verify.return_value = _google_payload()

        response = self.client.post("/api/auth/google/", {"id_token": "fake-token"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(email="buyer@example.com")
        self.assertFalse(user.has_usable_password())
        self.assertTrue(
            AuthProvider.objects.filter(
                user=user, provider="google", provider_user_id="google-user-123"
            ).exists()
        )

    @patch("apps.accounts.services.google_id_token.verify_oauth2_token")
    def test_repeat_sign_in_logs_into_same_user_without_duplicate_link(self, mock_verify):
        mock_verify.return_value = _google_payload()
        self.client.post("/api/auth/google/", {"id_token": "fake-token"})

        response = self.client.post("/api/auth/google/", {"id_token": "fake-token"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(User.objects.filter(email="buyer@example.com").count(), 1)
        self.assertEqual(AuthProvider.objects.count(), 1)

    @patch("apps.accounts.services.google_id_token.verify_oauth2_token")
    def test_links_google_to_existing_password_account_on_verified_email_match(self, mock_verify):
        existing_user = User.objects.create_user(email="buyer@example.com", password="s3cure-pass-1")
        mock_verify.return_value = _google_payload()

        response = self.client.post("/api/auth/google/", {"id_token": "fake-token"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["id"], existing_user.id)
        self.assertEqual(User.objects.filter(email="buyer@example.com").count(), 1)
        self.assertTrue(existing_user.has_usable_password())  # linking must not clear it

    @patch("apps.accounts.services.google_id_token.verify_oauth2_token")
    def test_rejects_unverified_email(self, mock_verify):
        mock_verify.return_value = _google_payload(email_verified=False)

        response = self.client.post("/api/auth/google/", {"id_token": "fake-token"})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(User.objects.filter(email="buyer@example.com").exists())

    @patch("apps.accounts.services.google_id_token.verify_oauth2_token")
    def test_rejects_invalid_token(self, mock_verify):
        mock_verify.side_effect = ValueError("bad signature")

        response = self.client.post("/api/auth/google/", {"id_token": "garbage"})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
