from django.utils import timezone

from apps.accounts.models import VendorProfile
from apps.accounts.vendor_services import apply_stripe_account_snapshot
from apps.delivery.services import grant_downloads_for_suborder, revoke_downloads_for_suborder
from apps.orders.models import Order, VendorSuborder


def _sync_order_status(order: Order) -> None:
    statuses = list(order.suborders.values_list("status", flat=True))
    if all(s == "paid" for s in statuses):
        order.status = "paid"
    elif any(s == "paid" for s in statuses):
        order.status = "partially_paid"
    elif statuses and all(s == "refunded" for s in statuses):
        order.status = "refunded"
    elif statuses and all(s == "failed" for s in statuses):
        order.status = "failed"
    else:
        return  # still pending — nothing to flip yet
    order.save(update_fields=["status"])


def handle_checkout_completed(event: dict) -> None:
    session = event["data"]["object"]
    try:
        suborder = VendorSuborder.objects.select_related("order").get(
            stripe_checkout_session_id=session["id"]
        )
    except VendorSuborder.DoesNotExist:
        return  # not one of ours (or a stale/foreign event) — nothing to do

    suborder.status = "paid"
    suborder.paid_at = timezone.now()
    # The PaymentIntent doesn't exist at Checkout Session creation time (confirmed live —
    # see orders/services.py's create_checkout_sessions), so this completed-session event
    # is the first point it's reliably available; back-fill it here for charge.refunded's
    # later lookup.
    suborder.stripe_payment_intent_id = session["payment_intent"]
    suborder.save(update_fields=["status", "paid_at", "stripe_payment_intent_id"])

    grant_downloads_for_suborder(suborder)
    _sync_order_status(suborder.order)


def handle_payment_failed(event: dict) -> None:
    payment_intent = event["data"]["object"]
    # Looked up by the suborder_id we stash in payment_intent_data.metadata at session
    # creation (see create_checkout_sessions) rather than by stripe_payment_intent_id — a
    # failed payment can happen before that field is ever back-filled, since it's only set
    # once checkout actually completes. Attribute access, not .get() — see the note in
    # accounts/vendor_services.py on why StripeObjects don't support dict methods.
    suborder_id = getattr(payment_intent["metadata"], "suborder_id", None)
    if not suborder_id:
        return

    try:
        suborder = VendorSuborder.objects.select_related("order").get(id=suborder_id)
    except VendorSuborder.DoesNotExist:
        return

    suborder.status = "failed"
    suborder.save(update_fields=["status"])
    _sync_order_status(suborder.order)


def handle_account_updated(event: dict) -> None:
    account = event["data"]["object"]
    try:
        vendor = VendorProfile.objects.get(stripe_account_id=account["id"])
    except VendorProfile.DoesNotExist:
        return

    # Shared with the return-URL sync in accounts/vendor_services.py — this webhook is what
    # actually flips a vendor to "complete" in the common case, since it can race the
    # buyer-driven return-URL page.
    apply_stripe_account_snapshot(vendor, account)


def handle_charge_refunded(event: dict) -> None:
    charge = event["data"]["object"]
    # Not dict-style .get() — see the identical note in accounts/vendor_services.py.
    payment_intent_id = getattr(charge, "payment_intent", None)
    if not payment_intent_id:
        return

    try:
        suborder = VendorSuborder.objects.select_related("order").get(
            stripe_payment_intent_id=payment_intent_id
        )
    except VendorSuborder.DoesNotExist:
        return

    suborder.status = "refunded"
    suborder.save(update_fields=["status"])
    revoke_downloads_for_suborder(suborder)
    _sync_order_status(suborder.order)


HANDLERS = {
    "checkout.session.completed": handle_checkout_completed,
    "payment_intent.payment_failed": handle_payment_failed,
    "account.updated": handle_account_updated,
    "charge.refunded": handle_charge_refunded,
}
