# Digital Goods Marketplace with Stripe Connect — Implementation Plan

## Context

This is project 3 of the 5-project portfolio rebuild. Projects 1 (RAG SaaS) and 2 (on-chain prediction market) both used FastAPI — project 3 needs to prove range: Django + DRF, the framework most enterprise/agency job postings still name explicitly, applied to a domain (payments/marketplace) that FastAPI portfolios rarely attempt well. The differentiator isn't "another CRUD app" — it's correct Stripe Connect split-payment mechanics and idempotent webhook handling, the part of marketplace engineering that actually separates senior from tutorial-level work. Auth, data model, and app structure are deliberately new shapes, not reskins of project 1's workspace multi-tenancy or project 2's SIWE flow.

Confirmed decision: a cart spanning multiple vendors creates one Stripe Checkout Session per vendor (buyer completes N checkouts for N vendors), not a single unified checkout — the honest, achievable-in-scope tradeoff vs. Stripe's more complex "Separate Charges and Transfers" pattern, which is named as a stretch goal.

## Stack (decided)

- Backend: Django 5.x + Django REST Framework (Python 3.12)
- DB: PostgreSQL
- Async/background jobs: Celery + Redis — narrow use only (order-confirmation email), not webhook processing itself (see §6)
- Auth: DRF + `djangorestframework-simplejwt` (access + refresh JWT), not Django session auth (see §5)
- Payments: Stripe Connect, **Express accounts**; **Stripe Checkout Session** for buyer payment
- Object storage: Cloudflare R2 (S3-compatible), presigned time-limited GET URLs via `boto3`
- Frontend: Next.js (App Router) + TypeScript
- Deploy: Vercel (web) / Railway (api + worker + Redis) / Railway or Neon Postgres

## 1. Data Model

Single `User` model (email as `USERNAME_FIELD`) with an optional `VendorProfile` extension — not two separate user tables. The common path is "buyer decides to start selling," and a forced Buyer/Vendor split would create an awkward identity-migration problem the first time that happens. A user with no `VendorProfile` is buyer-only; creating one unlocks vendor capabilities. One identity, additive roles.

**Real multi-item cart, not single-item checkout.** A cart can span multiple vendors — the scenario that breaks the naive "one Checkout Session, one `transfer_data.destination`" pattern, since a PaymentIntent has exactly one destination account. Building the cart forces the vendor-split design in §2 to be real, which is the project's core Stripe Connect proof point. Single-item MVP would make that story shallow.

```python
# accounts app
class User(AbstractUser):
    email = models.EmailField(unique=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

class VendorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="vendor_profile")
    store_name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(unique=True)
    stripe_account_id = models.CharField(max_length=64, blank=True)   # acct_...
    onboarding_status = models.CharField(max_length=20,
        choices=[("not_started","Not Started"),("pending","Pending"),
                 ("complete","Complete"),("restricted","Restricted")], default="not_started")
    charges_enabled = models.BooleanField(default=False)   # mirrors Stripe account.updated
    payouts_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

# catalog app
class Product(models.Model):
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name="products")
    title = models.CharField(max_length=200)
    slug = models.SlugField()
    description = models.TextField()
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES)  # template/preset/ebook/license/stock
    price_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="usd")
    status = models.CharField(max_length=20,
        choices=[("draft","Draft"),("published","Published"),("archived","Archived")], default="draft")
    cover_image_key = models.CharField(max_length=512, blank=True)   # R2 key, preview asset
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["vendor","slug"], name="uniq_vendor_product_slug")]

    objects = models.Manager()
    published = PublishedProductManager()   # .filter(status="published", vendor__charges_enabled=True)

class ProductFile(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="files")
    storage_key = models.CharField(max_length=512)     # private R2 key, never exposed directly
    original_filename = models.CharField(max_length=255)
    byte_size = models.BigIntegerField()
    content_type = models.CharField(max_length=127)
    sort_order = models.PositiveSmallIntegerField(default=0)

# orders app
class Cart(models.Model):
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="carts")
    status = models.CharField(max_length=20, choices=[("open","Open"),("converted","Converted")], default="open")
    created_at = models.DateTimeField(auto_now_add=True)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["cart","product"], name="uniq_cart_product")]

class Order(models.Model):
    # buyer-facing whole; may fan out into multiple VendorSuborders (multi-vendor cart)
    buyer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20,
        choices=[("pending","Pending"),("paid","Paid"),("partially_paid","Partially Paid"),
                 ("failed","Failed"),("refunded","Refunded")], default="pending")
    total_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="usd")
    created_at = models.DateTimeField(auto_now_add=True)

class VendorSuborder(models.Model):
    # one per vendor in the cart; each becomes its own Stripe Checkout Session (see §2)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="suborders")
    vendor = models.ForeignKey(VendorProfile, on_delete=models.PROTECT, related_name="suborders")
    subtotal_cents = models.PositiveIntegerField()
    platform_fee_cents = models.PositiveIntegerField()   # application_fee_amount for this suborder
    status = models.CharField(max_length=20,
        choices=[("pending","Pending"),("paid","Paid"),("failed","Failed"),("refunded","Refunded")],
        default="pending")
    stripe_checkout_session_id = models.CharField(max_length=128, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=128, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

class OrderLineItem(models.Model):
    suborder = models.ForeignKey(VendorSuborder, on_delete=models.CASCADE, related_name="line_items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    unit_price_cents = models.PositiveIntegerField()   # price snapshot at purchase time
    product_title_snapshot = models.CharField(max_length=200)  # survives product edits/deletion

# payments app
class StripeWebhookEvent(models.Model):
    # idempotency ledger — the whole retry-safety story keys off this table
    stripe_event_id = models.CharField(max_length=128, unique=True)   # evt_...
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    status = models.CharField(max_length=20,
        choices=[("received","Received"),("processed","Processed"),("failed","Failed"),("ignored","Ignored")],
        default="received")
    error_message = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

# delivery app
class DownloadGrant(models.Model):
    # ties a buyer to purchasable files for a specific line item — the access-control record
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="download_grants")
    line_item = models.ForeignKey(OrderLineItem, on_delete=models.CASCADE, related_name="download_grants")
    product_file = models.ForeignKey(ProductFile, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)   # refund path sets this

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["buyer","line_item","product_file"], name="uniq_grant_per_file")]

    # No expiry on the grant itself — it's permanent proof-of-purchase. Expiry lives on the
    # *signed URL*, generated fresh per request (see §3). Re-downloading forever is correct
    # marketplace UX (Gumroad/Creative Market behavior); one-time-link-then-dead is not.
```

**Key relationships/constraints**: `Product.vendor` cascades; `OrderLineItem`/`ProductFile` use `PROTECT` so a vendor can't delete a product that's been sold (archive instead — hides from catalog, preserves purchase history and grants). `VendorSuborder` is the actual unit of Stripe interaction; `Order` is a display/grouping convenience over 1+ suborders. `DownloadGrant` uniqueness is defense-in-depth against a webhook double-processing race; `StripeWebhookEvent` is the primary idempotency mechanism.

## 2. Stripe Connect Integration End-to-End

**Vendor onboarding (Express accounts)**: `POST /api/vendors/onboard` — if no `stripe_account_id` yet, `stripe.Account.create(type="express", ..., capabilities={"card_payments":{"requested":True},"transfers":{"requested":True}})`, store the id, `onboarding_status="pending"`. Always follow with `stripe.AccountLink.create(account=..., refresh_url=..., return_url=..., type="account_onboarding")` and return the URL for redirect. Stripe-hosted onboarding collects identity/bank details entirely off-platform. The **return URL** page doesn't trust the redirect as proof of success — it calls `GET /api/vendors/onboarding-status`, which retrieves the live Stripe account object and syncs status; the **refresh URL** just remints an AccountLink (they're single-use, short-lived) and redirects straight back into Stripe. A vendor can't publish products until `charges_enabled=True`, enforced at the service layer (not just hidden in UI) and doubly by `PublishedProductManager` filtering on `vendor__charges_enabled=True`.

**Checkout: Stripe Checkout Session, not raw PaymentIntents.** Zero PCI card handling in this codebase (mirrors the "let Stripe host the sensitive part" philosophy already used for onboarding); natively supports `line_items` for a real cart and `payment_intent_data.application_fee_amount`/`transfer_data.destination` for the Connect split in one call. A raw PaymentIntent + Elements integration would mean hand-building card UI and 3DS handling for no portfolio benefit — the interesting engineering here is the webhook/split logic, not payment-form UX.

**Multi-vendor split mechanic**: since `transfer_data.destination` accepts exactly one connected account per PaymentIntent, the cart decomposes into one `VendorSuborder` per represented vendor, and checkout creates **one Checkout Session per suborder** — each with that vendor's `line_items` only, its own `transfer_data.destination = vendor.stripe_account_id`, and its own `application_fee_amount`. `Order` is the buyer-facing grouping; `VendorSuborder` is what Stripe actually sees. The buyer flow presents this explicitly as "N charges, one per shop" at cart review. Stripe's "Separate Charges and Transfers" pattern (one PaymentIntent on the platform account, manual `Transfer` objects per vendor after the fact) is the real production alternative — named in the README as the natural next step, not silently skipped.

**Fee calculation**: `platform_fee_cents = round(subtotal_cents * PLATFORM_FEE_RATE)`, computed server-side at suborder-creation time (never trust a client-supplied amount), `PLATFORM_FEE_RATE = 0.15` as a `settings.py` constant for MVP (per-vendor negotiated rates are a stretch goal). Passed as `payment_intent_data={"application_fee_amount":..., "transfer_data":{"destination":...}}` on Checkout Session creation — Stripe splits funds atomically at charge time, no manual transfer needed for this destination-charge pattern.

**Checkout endpoint** (`POST /api/orders/checkout`): validate cart non-empty and every product still published/purchasable → `transaction.atomic()` creates `Order` (pending) + one `VendorSuborder` per distinct vendor + `OrderLineItem` rows with price snapshots → outside that transaction (network calls don't belong inside a DB transaction), call Stripe once per suborder for its Checkout Session, persist `stripe_checkout_session_id` → mark `Cart.status="converted"` → return session URLs; frontend redirects through them sequentially.

**Webhook flow** — `POST /api/webhooks/stripe`, CSRF-exempt, no auth decorator (signature verification *is* the auth):
1. **Signature verification**: `stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)`, reject 400 on failure before touching the DB. Plain `APIView` with `parser_classes=[]`, raw `request.body` read before any body-parsing middleware.
2. **Idempotency**: `StripeWebhookEvent.objects.get_or_create(stripe_event_id=event["id"], ...)`. If the row already existed (Stripe redelivers on retries/manual redelivery), return 200 immediately, no reprocessing.
3. Dispatch by `event["type"]`, each handler in its own `transaction.atomic()`:
   - **`checkout.session.completed`**: find `VendorSuborder` by session id, set `status="paid"`/`paid_at`; for each line item, `get_or_create` `DownloadGrant` rows (one per `ProductFile`) — redelivery-safe no-op. Flip `Order.status` to `"paid"` once all suborders paid, `"partially_paid"` if mixed.
   - **`payment_intent.payment_failed`**: find suborder by payment intent, `status="failed"`. No grants created; order page offers a retry-checkout action for just that suborder.
   - **`account.updated`**: find `VendorProfile` by `stripe_account_id`, sync `charges_enabled`/`payouts_enabled`/`onboarding_status` directly from the event payload (no extra API call) — this is what actually flips a vendor to "complete" in the common case, since it can race the return-URL sync.
   - **`charge.refunded`**: suborder `status="refunded"`, `revoked_at=now()` on its `DownloadGrant`s.
4. Handler exceptions: mark `StripeWebhookEvent.status="failed"` + `error_message`, **re-raise to return 5xx** — swallowing and returning 200 would silently lose the event forever; a 5xx is what makes Stripe's retry schedule actually fire. Success → `status="processed"`.
5. Webhook processing stays **synchronous** in-request, no Celery hand-off (see §6).

## 3. Digital Delivery Mechanism

**Grant vs. signed URL — deliberately different lifetimes.** `DownloadGrant` is permanent proof-of-purchase, created once at `checkout.session.completed`. The signed URL is disposable and regenerated on demand — this is what makes "redownload months later from the orders page" work correctly, instead of the common mistake of baking one long-lived link into a confirmation email that eventually 403s.

`GET /api/orders/{order_id}/downloads` — called immediately post-purchase or any time later from an orders page: for each non-revoked `DownloadGrant` the requesting user owns, generate a **fresh** presigned R2 GET URL (`boto3.generate_presigned_url("get_object", ..., ExpiresIn=600)`, 10 minutes — long enough to complete a download, short enough that a leaked link is quickly worthless). Nothing about the specific URL is persisted; it's computed per request and discarded.

Authorization happens *before* URL generation, at the Django/DRF layer, not via R2 key obscurity: `DownloadGrant.objects.filter(buyer=request.user, line_item__suborder__order_id=order_id, revoked_at__isnull=True)` — a buyer can only ever generate URLs for their own grants, and a refunded purchase's grants (revoked by the webhook handler) silently drop out of this queryset with no separate "check if refunded" branch needed. R2 keys use a non-guessable path (`products/{product_id}/files/{product_file_id}/{filename}`, UUID file id) as a second layer, though the bucket is fully private regardless. Vendor product upload uses presigned PUT (not proxying large files through the Django app server) since digital goods here can include sizeable stock-asset ZIPs.

## 4. Django/DRF Architecture — What Reads as Senior, Not Tutorial

**App structure**, one responsibility per app: `accounts` (User, VendorProfile, JWT auth, onboarding), `catalog` (Product, ProductFile, storefront), `orders` (Cart, Order, VendorSuborder, OrderLineItem, checkout orchestration), `payments` (StripeWebhookEvent, webhook endpoint, Stripe wrapper), `delivery` (DownloadGrant, signed-URL endpoint).

**Service layer over signals — explicit choice.** Signals fire inside the sender's transaction by default and create implicit, hard-to-trace control flow with fragile multi-receiver ordering — exactly wrong for a payment webhook creating access grants, which needs to be traceable in a stack trace and testable as a plain function call. So: explicit service-layer functions, one per meaningful state transition (`orders/services.py: create_order_from_cart()`, `payments/services.py: handle_checkout_completed(event)`, `delivery/services.py: grant_downloads_for_suborder(suborder)`), called directly from the view/handler that owns the transaction. Named explicitly in the README as a deliberate signals-vs-services tradeoff — a legitimate senior-level interview topic.

**`transaction.atomic()` boundaries that matter**: `create_order_from_cart()` wraps `Order` + all `VendorSuborder`/`OrderLineItem` creation atomically (a partially-converted cart is a real correctness bug, not hypothetical). Each webhook handler gets its own `atomic()` block scoped per event, not one transaction for the whole webhook request, so one malformed event in a batch fails/retries independently. Deliberately **not** using `select_for_update()` on `VendorSuborder` for MVP — the `get_or_create` on `StripeWebhookEvent.stripe_event_id` is the actual concurrency guard for duplicate deliveries of the same event; named as a stretch hardening item, not silently skipped.

**Managers/querysets**: `Product.published` is the *only* queryset the public catalog API touches — vendor draft/archived products can't leak through a generic `.all()` call by accident, because public views don't import it. `VendorProfile.is_onboarded` is a computed property (`charges_enabled and payouts_enabled`), not a duplicated stored field.

**DRF organization**: `ModelViewSet` for straightforward CRUD, but `ProductViewSet` (vendor-scoped, `get_queryset` filtered to `request.user.vendor_profile`) and `PublicProductViewSet` (read-only, `Product.published`) are two separate viewsets, not one with conditional logic, since their permission and queryset shapes genuinely differ. Plain `APIView` for non-CRUD actions (`CheckoutView`, `StripeWebhookView`, `VendorOnboardingView`, `DownloadListView`) rather than forcing everything into viewset actions. Serializers separate read/write shapes where they diverge — the public product serializer never has a path to leak `vendor.stripe_account_id` because the field isn't declared on it.

**Auth base**: `AbstractUser` subclass, not `AbstractBaseUser` from scratch — no reason to hand-roll password hashing Django already provides correctly; only email-as-username needs overriding.

## 5. Auth

**DRF + `simplejwt` (JWT access + refresh), not Django session auth.** Next.js (Vercel) and Django (Railway) are separate origins, same cross-origin split as project 1. Session auth would mean `SameSite=None` cross-site cookies plus CSRF plumbing through every mutating request with no same-origin `{% csrf_token %}` template tag to lean on. JWT sidesteps that entirely and is the pattern expected for a decoupled SPA-style frontend — and it's a chance to show the *same* rotation discipline as project 1 through Django's idiomatic library, proving the Django-native way, not a copy-paste.

Flow: `POST /api/auth/register`, `POST /api/auth/token/` (`simplejwt`'s `TokenObtainPairView`, subclassed to also return the serialized `User`) → access token (10 min) in body, refresh token (7 days) as `HttpOnly`/`Secure`/`SameSite=None` cookie (not body — inaccessible to JS/XSS). `ROTATE_REFRESH_TOKENS=True` + `BLACKLIST_AFTER_ROTATION=True` (via `rest_framework_simplejwt.token_blacklist`) gives rotation-with-revocation for free. `POST /api/auth/token/refresh/` reads the cookie, issues a new pair; `POST /api/auth/logout` blacklists the current refresh token.

## 6. Repo Structure & Celery Decision

**Celery: needed, but narrow** — not for webhook processing (must stay synchronous and fast so Stripe sees a prompt 200; the handler work is a handful of DB writes, milliseconds), but for the one genuinely slow/best-effort post-payment task: sending the order confirmation email with download links. Email delivery is exactly the variable-latency, retry-tolerant, non-blocking work Celery exists for — a legitimate second, smaller use case distinct from project 1's ingestion pipeline, without inventing async infrastructure around the payment-critical path. Redis is required regardless as the Celery broker.

```
digital-goods-marketplace/
├── api/                              # Django + DRF
│   ├── config/                       # settings, urls, celery_app.py
│   ├── apps/
│   │   ├── accounts/                 # User, VendorProfile, auth views, onboarding
│   │   ├── catalog/                  # Product, ProductFile, storefront + vendor CRUD
│   │   ├── orders/                   # Cart, Order, VendorSuborder, OrderLineItem, checkout
│   │   │   └── services.py           # create_order_from_cart(), create_checkout_sessions()
│   │   ├── payments/                 # StripeWebhookEvent, webhook view, stripe_client.py
│   │   │   ├── services.py           # handle_checkout_completed(), handle_account_updated(), etc.
│   │   │   └── tasks.py              # send_order_confirmation_email.delay(order_id)
│   │   └── delivery/                 # DownloadGrant, signed-URL endpoint, r2_client.py
│   ├── tests/                        # webhook idempotency + fee-split are the two suites to over-invest in
│   ├── manage.py
│   ├── pyproject.toml
│   └── Dockerfile
├── web/                               # Next.js + TypeScript
│   ├── app/
│   │   ├── (storefront)/{page,products/[slug]}.tsx
│   │   ├── cart/page.tsx
│   │   ├── checkout/return/page.tsx                     # per-suborder success_url landing
│   │   ├── orders/[id]/page.tsx                          # order status + download buttons
│   │   ├── vendor/{dashboard,products,onboarding}/*.tsx
│   │   └── (auth)/{login,register}/page.tsx
│   ├── lib/{apiClient.ts,auth.ts}
│   ├── package.json
│   └── next.config.ts
├── docker-compose.yml                 # postgres + redis + api + celery worker
├── .env.example
└── README.md                          # Connect split mechanics, webhook idempotency,
                                        # signals-vs-services decision, multi-vendor-cart tradeoff
```

## 7. MVP vs Stretch

**MVP**: email/password auth via `simplejwt` with refresh rotation + blacklisting; one `User` model with optional `VendorProfile`; vendor Express-account onboarding (AccountLink, return/refresh URLs, `account.updated`-driven status sync); vendor product CRUD with multi-file R2 upload (presigned PUT); public storefront browse/search/filter; real multi-item cart; checkout fanning a multi-vendor cart into per-vendor Checkout Sessions with correct fee/destination split; full webhook handling (all four events) with signature verification and idempotency ledger; `DownloadGrant` creation on payment success; fresh signed-URL generation on every download request; order history with per-vendor status; Celery confirmation email; public deploy with a seeded demo (a few vendors, published products, one pre-completed test purchase).

**Stretch**: Stripe balance/payout dashboard view; coupon codes; product reviews; vendor-initiated refund UI (currently Dashboard-only, webhook-reflected); "Separate Charges and Transfers" as a unified-checkout alternative; per-vendor negotiated fee rates; `select_for_update()` webhook hardening; DRF rate limiting on checkout/webhook endpoints; full-text product search; vendor sales-analytics dashboard; download-count limiting on grants.

## 8. Build Order

- **M1 — Accounts, Catalog, Vendor Onboarding.** `User`/`VendorProfile`, `simplejwt` auth, Express-account creation + AccountLink + return/refresh routes + `account.updated` webhook wired to onboarding status, product CRUD with R2 upload, public storefront browse. *Demo*: register as vendor, complete Stripe test-mode onboarding, see `charges_enabled` flip true, publish a product with a file, see it in the public catalog.
- **M2 — Cart, Checkout, Stripe Connect Split.** `Cart`/`CartItem`, `create_order_from_cart()`, per-vendor `VendorSuborder` decomposition, Checkout Session creation with fee/destination split, full webhook endpoint (all four handlers, idempotency ledger). *Demo*: cart spanning two test-mode vendor accounts, complete both Checkout Sessions with test cards, verify the application fee landed on the platform account and the remainder on each connected account in the Stripe Dashboard; replay a webhook event and show it's a no-op the second time.
- **M3 — Delivery + Orders.** `DownloadGrant` creation on payment success, signed-URL endpoint, orders history page, Celery confirmation email, refund webhook revoking grants. *Demo*: purchase → immediate download via signed URL → return to orders page "later" and download again with a freshly generated URL → trigger a test refund and show the download button disappears.
- **M4 — Frontend Polish + Deploy.** Full storefront/cart/checkout/vendor-dashboard UI, error/empty/loading states, seed script, deploy web→Vercel / api+worker→Railway / db→Railway-or-Neon, Stripe webhook registered against the deployed URL, README write-up. *Demo*: a stranger browses with no login, registers, buys a multi-vendor cart with a Stripe test card, lands on a working order/downloads page, and separately registers as a vendor, onboards, and publishes a product — all against the live deploy.

## Critical Files

- `api/apps/payments/services.py` — webhook event handlers (idempotency + Connect state transitions); the project's technical centerpiece
- `api/apps/orders/services.py` — `create_order_from_cart()` and the multi-vendor cart → per-vendor suborder/Checkout Session decomposition
- `api/apps/orders/models.py` / `api/apps/payments/models.py` — `Order`/`VendorSuborder`/`OrderLineItem`/`StripeWebhookEvent` schema from §1
- `api/apps/delivery/services.py` — signed URL generation + grant authorization logic (§3)
- `api/config/settings.py` — `simplejwt` config, Stripe keys, R2 wiring

## Verification

- **M1**: register a vendor, complete Stripe test-mode onboarding end-to-end, confirm `charges_enabled` flips via the `account.updated` webhook; publish a product and confirm it's excluded from the public catalog until `charges_enabled=True`.
- **M2**: complete a two-vendor cart checkout with Stripe test cards; confirm in the Stripe Dashboard that each connected account received its correct split and the platform account received the combined application fee; use the Stripe CLI to redeliver a `checkout.session.completed` event and confirm no duplicate `DownloadGrant`/state change occurs.
- **M3**: complete a purchase, download immediately, then call the downloads endpoint again and confirm a *different* signed URL is returned each time; issue a test refund and confirm the grant's `revoked_at` is set and the download endpoint no longer includes it.
- **M4**: open the deployed Vercel URL in a private browser window, register fresh, complete a real multi-vendor test-mode purchase, and complete the full vendor-onboarding-to-published-product flow — end to end, no prior state, no manual backend intervention.
