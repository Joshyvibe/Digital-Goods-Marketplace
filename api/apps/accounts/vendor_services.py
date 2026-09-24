from django.conf import settings
from django.utils.text import slugify

from apps.payments.stripe_client import stripe

from .models import User, VendorProfile


class VendorOnboardingError(Exception):
    """Raised when a Stripe onboarding step fails (network/API error) or a precondition
    isn't met. Callers turn this into a 4xx without leaking Stripe's internal detail."""


def _unique_slug(store_name: str) -> str:
    base = slugify(store_name)
    slug = base
    suffix = 1
    while VendorProfile.objects.filter(slug=slug).exists():
        suffix += 1
        slug = f"{base}-{suffix}"
    return slug


def get_or_create_vendor_profile(user: User, store_name: str) -> VendorProfile:
    if hasattr(user, "vendor_profile"):
        return user.vendor_profile
    return VendorProfile.objects.create(
        user=user, store_name=store_name, slug=_unique_slug(store_name)
    )


def ensure_stripe_account(vendor: VendorProfile) -> VendorProfile:
    """Creates the Express connected account on first call; a no-op on every call after —
    Stripe accounts, once created, are reused for the life of the vendor."""
    if vendor.stripe_account_id:
        return vendor

    try:
        account = stripe.Account.create(
            type="express",
            email=vendor.user.email,
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
        )
    except stripe.StripeError as exc:
        raise VendorOnboardingError("Could not create Stripe account") from exc

    vendor.stripe_account_id = account.id
    vendor.onboarding_status = "pending"
    vendor.save(update_fields=["stripe_account_id", "onboarding_status"])
    return vendor


def create_onboarding_link(vendor: VendorProfile) -> str:
    """AccountLinks are single-use and short-lived (a few minutes) — always mint a fresh
    one per request, never cache/reuse the URL."""
    if not vendor.stripe_account_id:
        raise VendorOnboardingError("Vendor has no Stripe account yet")

    try:
        account_link = stripe.AccountLink.create(
            account=vendor.stripe_account_id,
            refresh_url=f"{settings.FRONTEND_URL}/vendor/onboarding?refresh=1",
            return_url=f"{settings.FRONTEND_URL}/vendor/onboarding?return=1",
            type="account_onboarding",
        )
    except stripe.StripeError as exc:
        raise VendorOnboardingError("Could not create onboarding link") from exc

    return account_link.url


def sync_onboarding_status(vendor: VendorProfile) -> VendorProfile:
    """Pulls the live Stripe Account object and syncs local status from it. This is the
    return-URL page's source of truth — the redirect itself is never trusted as proof of
    completion (see apps/payments for the account.updated webhook, the other sync path)."""
    if not vendor.stripe_account_id:
        return vendor

    try:
        account = stripe.Account.retrieve(vendor.stripe_account_id)
    except stripe.StripeError as exc:
        raise VendorOnboardingError("Could not retrieve Stripe account") from exc

    apply_stripe_account_snapshot(vendor, account)
    return vendor


def apply_stripe_account_snapshot(vendor: VendorProfile, account) -> None:
    """Shared by the return-URL sync above and the account.updated webhook handler (M2) —
    both ultimately just mirror fields off a Stripe Account object onto VendorProfile."""
    vendor.charges_enabled = bool(account["charges_enabled"])
    vendor.payouts_enabled = bool(account["payouts_enabled"])

    # Not dict-style .get() — recent stripe-python StripeObjects reserve dict method names
    # (.get, .items, ...) and raise AttributeError if you call them on a nested object;
    # plain attribute access is the correct way to read a field that may be null/absent.
    if vendor.charges_enabled and vendor.payouts_enabled:
        vendor.onboarding_status = "complete"
    elif getattr(account["requirements"], "disabled_reason", None):
        vendor.onboarding_status = "restricted"
    else:
        vendor.onboarding_status = "pending"

    vendor.save(update_fields=["charges_enabled", "payouts_enabled", "onboarding_status"])
