from django.conf import settings
from django.db import transaction

from apps.accounts.models import User
from apps.catalog.models import Product
from apps.payments.stripe_client import stripe

from .models import Cart, CartItem, Order, OrderLineItem, VendorSuborder


class CartError(Exception):
    """A cart mutation that can't proceed — bad product state, not the user's cart, etc."""


class CheckoutError(Exception):
    """Raised for any precondition failure or Stripe API error during checkout. Callers
    turn this into a 4xx/502 without leaking Stripe's internal detail."""


def get_or_create_open_cart(buyer: User) -> Cart:
    cart, _ = Cart.objects.get_or_create(buyer=buyer, status="open")
    return cart


def add_item_to_cart(cart: Cart, product: Product) -> CartItem:
    if product.status != "published" or not product.vendor.charges_enabled:
        raise CartError("This product is not available for purchase.")
    item, _ = CartItem.objects.get_or_create(cart=cart, product=product)
    return item


def remove_item_from_cart(cart: Cart, product_id: int) -> None:
    CartItem.objects.filter(cart=cart, product_id=product_id).delete()


def create_order_from_cart(cart: Cart) -> Order:
    """Validates the cart, then atomically creates Order + one VendorSuborder per
    represented vendor + OrderLineItem rows with price snapshots. Does NOT call Stripe —
    see create_checkout_sessions() below, kept out of this transaction because network
    calls don't belong inside a DB transaction (see SYSTEM_DESIGN.md / PLAN.md §2, §4)."""
    items = list(cart.items.select_related("product", "product__vendor"))
    if not items:
        raise CheckoutError("Your cart is empty.")

    for item in items:
        product = item.product
        if product.status != "published" or not product.vendor.charges_enabled:
            raise CheckoutError(f'"{product.title}" is no longer available for purchase.')

    items_by_vendor: dict[int, list[CartItem]] = {}
    for item in items:
        items_by_vendor.setdefault(item.product.vendor_id, []).append(item)

    with transaction.atomic():
        total_cents = sum(item.product.price_cents for item in items)
        order = Order.objects.create(buyer=cart.buyer, total_cents=total_cents, currency="usd")

        for vendor_items in items_by_vendor.values():
            vendor = vendor_items[0].product.vendor
            subtotal_cents = sum(i.product.price_cents for i in vendor_items)
            # Server-computed, always — never trust a client-supplied fee amount.
            platform_fee_cents = round(subtotal_cents * settings.PLATFORM_FEE_RATE)

            suborder = VendorSuborder.objects.create(
                order=order,
                vendor=vendor,
                subtotal_cents=subtotal_cents,
                platform_fee_cents=platform_fee_cents,
            )
            for item in vendor_items:
                OrderLineItem.objects.create(
                    suborder=suborder,
                    product=item.product,
                    unit_price_cents=item.product.price_cents,
                    product_title_snapshot=item.product.title,
                )

        cart.status = "converted"
        cart.save(update_fields=["status"])

    return order


def create_checkout_sessions(order: Order, suborders=None) -> list[str]:
    """One Stripe Checkout Session per suborder — each with only that vendor's line items,
    its own transfer_data.destination, and its own application_fee_amount. Stripe splits
    funds atomically at charge time via the destination-charge pattern.

    `suborders` lets a caller scope this to a subset (see retry_suborder_checkout below);
    defaults to every suborder on the order, which is what checkout_cart() wants."""
    checkout_urls = []
    suborders = order.suborders.all() if suborders is None else suborders

    for suborder in suborders.select_related("vendor").prefetch_related("line_items"):
        line_items = [
            {
                "price_data": {
                    "currency": order.currency,
                    "product_data": {"name": line_item.product_title_snapshot},
                    "unit_amount": line_item.unit_price_cents,
                },
                "quantity": 1,
            }
            for line_item in suborder.line_items.all()
        ]

        try:
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=line_items,
                payment_intent_data={
                    "application_fee_amount": suborder.platform_fee_cents,
                    "transfer_data": {"destination": suborder.vendor.stripe_account_id},
                    # The PaymentIntent isn't created until the buyer actually reaches
                    # payment (confirmed live — session.payment_intent is None right after
                    # Session.create(), contrary to older docs/assumptions), so it can't be
                    # looked up by id yet. Metadata set here propagates onto the PI whenever
                    # it *does* get created, which is what makes payment_intent.payment_failed
                    # able to find this suborder even though no PI existed at session-creation
                    # time.
                    "metadata": {"suborder_id": str(suborder.id)},
                },
                success_url=f"{settings.FRONTEND_URL}/checkout/return?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.FRONTEND_URL}/cart",
            )
        except stripe.StripeError as exc:
            raise CheckoutError("Could not start checkout with Stripe.") from exc

        suborder.stripe_checkout_session_id = session.id
        suborder.save(update_fields=["stripe_checkout_session_id"])

        checkout_urls.append(session.url)

    return checkout_urls


def checkout_cart(cart: Cart) -> tuple[Order, list[str]]:
    """The full checkout orchestration: create_order_from_cart() + create_checkout_sessions(),
    but if Stripe rejects any session, roll back cleanly — delete the just-created Order and
    reopen the cart — rather than leaving the buyer's cart silently "converted" with an
    abandoned, unpayable order behind it (caught via live testing: a vendor whose Stripe
    account isn't actually capable of receiving transfers fails at session-creation time,
    and without this rollback the buyer's cart would appear to empty itself on next load)."""
    order = create_order_from_cart(cart)
    try:
        checkout_urls = create_checkout_sessions(order)
    except Exception:
        # Broad on purpose: *any* failure past this point (not just the StripeError case
        # create_checkout_sessions wraps as CheckoutError) must not leave the cart orphaned.
        order.delete()
        cart.status = "open"
        cart.save(update_fields=["status"])
        raise
    return order, checkout_urls


def retry_suborder_checkout(suborder: VendorSuborder) -> list[str]:
    """A pending suborder means the buyer reached Stripe Checkout but never completed it
    (abandoned, browser closed, etc.) — the session itself expires on Stripe's side, but
    nothing here ever retries automatically, so give the buyer a fresh session for just
    this suborder rather than making them re-add everything to a cart and re-checkout."""
    if suborder.status != "pending":
        raise CheckoutError("This item isn't pending — there's nothing to retry.")

    for line_item in suborder.line_items.select_related("product__vendor"):
        product = line_item.product
        if product.status != "published" or not product.vendor.charges_enabled:
            raise CheckoutError(f'"{product.title}" is no longer available for purchase.')

    return create_checkout_sessions(
        suborder.order, suborders=VendorSuborder.objects.filter(id=suborder.id)
    )


def cancel_pending_suborder(suborder: VendorSuborder) -> None:
    """Drops an abandoned checkout attempt. Safe to hard-delete: a pending suborder was
    never paid, so it has no DownloadGrant, no vendor payout, nothing else referencing it —
    unlike a paid/refunded suborder, which this deliberately refuses to touch."""
    if suborder.status != "pending":
        raise CheckoutError("Only a pending item can be cancelled.")

    order = suborder.order
    with transaction.atomic():
        suborder.delete()
        remaining = list(order.suborders.all())
        if remaining:
            order.total_cents = sum(s.subtotal_cents for s in remaining)
            order.save(update_fields=["total_cents"])
        else:
            order.delete()
