from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework_simplejwt.tokens import RefreshToken

from django.conf import settings

from .models import AuthProvider, User


class GoogleAuthError(Exception):
    """Raised for any verification/policy failure in the Google sign-in flow.
    Callers turn this into a 401 without leaking which specific check failed."""


def verify_google_id_token(raw_id_token: str) -> dict:
    try:
        payload = google_id_token.verify_oauth2_token(
            raw_id_token, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
        )
    except ValueError as exc:
        raise GoogleAuthError("Invalid Google ID token") from exc

    if not payload.get("email_verified"):
        raise GoogleAuthError("Google account email is not verified")

    return payload


def authenticate_or_create_google_user(raw_id_token: str) -> User:
    """Find-or-create the User behind a verified Google ID token.

    Three paths, in order:
    1. This Google account has signed in before -> log in that user.
    2. No AuthProvider row, but a User already exists with this email (they registered
       with a password first) -> link Google to that account. Safe only because
       verify_google_id_token() already confirmed Google itself vouches for the email;
       auto-linking on an unverified email would be an account-takeover vector.
    3. Neither exists -> create a new User with an unusable password (Google-only account).
    """
    payload = verify_google_id_token(raw_id_token)
    provider_user_id = payload["sub"]
    email = payload["email"]

    auth_provider = (
        AuthProvider.objects.select_related("user")
        .filter(provider="google", provider_user_id=provider_user_id)
        .first()
    )
    if auth_provider:
        return auth_provider.user

    user, created = User.objects.get_or_create(
        email=email,
        defaults={"first_name": payload.get("given_name", "")},
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])

    AuthProvider.objects.create(
        user=user, provider="google", provider_user_id=provider_user_id, email=email
    )
    return user


def issue_token_pair(user: User) -> tuple[str, str]:
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


def set_refresh_cookie(response, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path="/api/auth/",
    )


def clear_refresh_cookie(response) -> None:
    response.delete_cookie(settings.REFRESH_TOKEN_COOKIE_NAME, path="/api/auth/")


def delete_or_deactivate_account(user: User) -> str:
    """Hard-deletes the account if nothing depends on it; otherwise deactivates and
    anonymizes it instead. Returns "deleted" or "deactivated".

    Order.buyer and OrderLineItem.product both use on_delete=PROTECT deliberately —
    financial/purchase history must never silently disappear, and a buyer's download
    access depends on their purchased products' rows surviving. That means a user with
    any order history at all (as buyer, or as a vendor who's sold anything) can't be
    hard-deleted; Django would raise ProtectedError. Soft-deleting is the correct fallback:
    is_active=False immediately invalidates every outstanding access token (simplejwt's
    JWTAuthentication rejects inactive users on every request, not just future logins),
    and anonymizing the email satisfies "delete my account" without breaking anyone else's
    order integrity.
    """
    from apps.orders.models import Order, OrderLineItem

    has_orders = Order.objects.filter(buyer=user).exists()
    has_vendor_sales = hasattr(user, "vendor_profile") and OrderLineItem.objects.filter(
        product__vendor=user.vendor_profile
    ).exists()

    if not has_orders and not has_vendor_sales:
        user.delete()
        return "deleted"

    if hasattr(user, "vendor_profile"):
        # Unsold products of a deactivating vendor are still cascade-safe to hide; sold
        # ones (PROTECT) simply can't be deleted, but archiving is a status update, not a
        # delete, so it applies to all of them uniformly.
        user.vendor_profile.products.exclude(status="archived").update(status="archived")

    user.email = f"deleted-user-{user.id}@deleted.invalid"
    user.first_name = ""
    user.last_name = ""
    user.is_active = False
    user.set_unusable_password()
    user.save()
    return "deactivated"
