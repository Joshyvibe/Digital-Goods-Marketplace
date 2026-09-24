# Digital Goods Marketplace — System Design (v2)

Supersedes nothing in [PLAN.md](./PLAN.md) — it's the base architecture and stays correct. This document layers on two changes the base plan didn't cover, then restates the full feature set as one reviewable spec:

1. **Google OAuth** as a first-class signup/login path alongside email/password.
2. **Feature-sliced frontend folder structure** (`features/` on the frontend; the backend's `apps/` already plays this role).

Everything else — data model, Stripe Connect split mechanics, webhook idempotency, delivery, service-layer-over-signals — is unchanged from PLAN.md §1–4, §6–8. This doc references those sections rather than repeating them, except where a section needs a diff.

---

## 1. Requirements

**Functional** (full list in §5 below) — buyer storefront/cart/checkout, vendor onboarding/catalog management, digital delivery, order history, dual-path auth (password + Google).

**Non-functional** — this is a portfolio project, not a production marketplace: optimize for *demonstrable correctness* (idempotent webhooks, correct fee splits, secure delivery) over throughput. No specific RPS/latency SLA. Single-region deploy is fine. Security and auth correctness matter more than scale here, since that's what a reviewer will actually probe.

**Constraints** — solo build, Django + DRF backend (already decided, see PLAN.md stack rationale), Next.js App Router frontend, Stripe test mode throughout, Vercel/Railway deploy target.

---

## 2. Auth Design (updated)

### 2.1 Decision: verify Google's ID token server-side, don't split auth systems

Three ways to add Google sign-in were on the table:

| Option | Verdict |
|---|---|
| **NextAuth.js (Auth.js) on the frontend**, Google as a NextAuth provider | Rejected. NextAuth would own its own session/JWT, separate from the Django-issued `simplejwt` tokens the password flow already uses. That's two auth systems issuing two different tokens for the same user — the frontend would need to know which one is active. Wrong shape for a backend that's supposed to be the single source of truth. |
| **`django-allauth` + `dj-rest-auth`** on the backend | Rejected. Pulls in Django's session/template-based auth machinery this project deliberately opted out of (PLAN.md §5 — JWT was chosen specifically to avoid cross-origin cookie/CSRF plumbing). Also heavier than needed for one provider. |
| **Google Identity Services (GIS) on the frontend → verify ID token on the backend → issue the same `simplejwt` pair** | **Chosen.** Google's GIS JS library (the current, non-deprecated Google Sign-In integration as of 2026) renders the button/One Tap and hands back a signed ID token — a JWT Google already vouches for. The backend verifies it with Google's public keys and, on success, runs through the *exact same* token-issuance code path as password login. One auth system, one token format, two ways to arrive at it. |

This keeps the identity model from PLAN.md §1 intact — one `User`, auth method is just how they got a session, not a second identity table.

### 2.2 Data model addition

```python
# accounts app
class AuthProvider(models.Model):
    # links a User to an external identity provider; email/password users have zero rows here
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="auth_providers")
    provider = models.CharField(max_length=20, choices=[("google", "Google")])
    provider_user_id = models.CharField(max_length=255)   # Google's `sub` claim — stable, unlike email
    email = models.EmailField()                            # snapshot at link time, for audit/debugging
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["provider", "provider_user_id"], name="uniq_provider_account")]
```

`User.password` allows Django's `set_unusable_password()` for Google-only signups — no password row, `has_usable_password()` gates whether the frontend shows a "set a password" option later. Modeling as a separate `AuthProvider` table (not a `google_sub` column on `User`) is deliberate: it's the only shape that doesn't need a schema change to add GitHub/Apple later — a real possibility across 5 portfolio projects reusing this pattern.

### 2.3 Flow

**Frontend**: `next/script` loads `https://accounts.google.com/gsi/client`; GIS renders the Sign-in-with-Google button. On success, GIS calls back with `response.credential` — a signed JWT ID token, not an access token, so no OAuth redirect dance or popup-blocker risk. POST it to the backend as-is.

**Backend** — `POST /api/auth/google/`, body `{"id_token": "..."}`, handled by `accounts/services.py: authenticate_or_create_google_user()`:

1. Verify with `google.oauth2.id_token.verify_oauth2_token(token, google.auth.transport.requests.Request(), settings.GOOGLE_CLIENT_ID)` — this checks signature (against Google's rotating public keys), expiry, and `aud` match in one call. Reject 401 on any failure before touching the DB, same posture as Stripe webhook signature verification in PLAN.md §2.
2. Extract `sub`, `email`, `email_verified`, `name` from the verified payload.
3. **Reject if `email_verified` is `False`** — don't trust an unverified email as proof of identity.
4. Look up `AuthProvider.objects.filter(provider="google", provider_user_id=sub)`:
   - **Found** → log in that user. Done.
   - **Not found** → look up `User` by email:
     - **Existing password user, same email** → this is an account-linking case, not a new signup. Only auto-link because step 3 already confirmed Google verified the email — create the `AuthProvider` row against the existing user, log in. (If `email_verified` were `False` here, refuse and tell the user to log in with their password instead — auto-linking on an unverified email is a real account-takeover vector and worth calling out explicitly.)
     - **No existing user** → create `User` (email, `set_unusable_password()`), create `AuthProvider` row, log in.
5. Issue the identical `simplejwt` access + refresh pair as `TokenObtainPairView` (PLAN.md §5) — same response shape, same `HttpOnly`/`Secure`/`SameSite=None` refresh cookie, same rotation/blacklist config. The frontend's post-login code doesn't need to know which path was used.

**Endpoint surface added to §5's auth flow:**

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/auth/google/` | Verify Google ID token, find-or-create user, issue JWT pair |

No separate `/api/auth/google/callback` — GIS's credential flow is not a redirect-based OAuth flow, so there's no server-side callback leg to build.

---

## 3. Full Feature List

### Buyer
- Register / log in with email + password
- Register / log in with Google (One Tap or button)
- Browse storefront: search, filter by category
- Product detail page
- Multi-vendor cart (add/remove/update)
- Cart review showing per-vendor breakdown ("N charges, one per shop")
- Checkout: sequential per-vendor Stripe Checkout Sessions
- Order history with per-suborder status (pending / paid / partially paid / failed / refunded)
- Download purchased files — fresh signed URL generated per request, works indefinitely post-purchase
- Refund reflected automatically: download access revoked, no manual step

### Vendor (additive role on the same `User` — see PLAN.md §1)
- "Become a vendor" — creates `VendorProfile`
- Stripe Express onboarding via hosted `AccountLink` (identity/bank collected entirely off-platform)
- Onboarding status synced two ways: return-URL page + `account.updated` webhook (source of truth)
- Product CRUD: create/edit/publish/archive
- Multi-file upload per product via presigned PUT direct to R2 (no large files through the app server)
- Vendor dashboard: product list, onboarding status, suborders received

### Platform / Support
- Django Admin over all models — no dedicated admin frontend for MVP (not worth building for a single-operator platform)
- `StripeWebhookEvent` ledger visible in admin for support/debugging a specific delivery

### Cross-cutting system features
- JWT auth (access + refresh) with rotation + blacklist on logout
- Google OAuth as a second, backend-verified auth path (this doc, §2)
- Idempotent Stripe webhook processing (event-id ledger, PLAN.md §2)
- Server-computed platform fee, never client-supplied
- Celery-driven order confirmation email (only async task in the payment-critical path)
- Presigned, time-limited, per-request download URLs (PLAN.md §3)
- Seed script producing a working demo: a few vendors, published products, one pre-completed purchase

---

## 4. High-Level Architecture

```
                     ┌─────────────────────────┐
                     │   Next.js (Vercel)      │
                     │   App Router + features/│
                     └────────────┬────────────┘
                                  │ HTTPS (JWT access token / HttpOnly refresh cookie)
                                  ▼
                     ┌─────────────────────────┐        ┌──────────────┐
                     │   Django + DRF (Railway)│◄──────►│  PostgreSQL  │
                     │   apps/{accounts,catalog,│        └──────────────┘
                     │   orders,payments,delivery}│
                     └───┬──────────┬───────┬───┘
                         │          │       │
             signed URLs │   webhook│       │ enqueue
                         ▼          ▼       ▼
                  ┌───────────┐ ┌───────┐ ┌──────────────┐
                  │Cloudflare │ │Stripe │ │ Celery worker │
                  │   R2      │ │       │ │  + Redis      │
                  └───────────┘ └───────┘ └──────────────┘
                                  ▲
                                  │ ID token verification (Google public keys)
                                  │
                          Google Identity Services
                          (browser-side, no server callback)
```

---

## 5. Folder Structure

### Backend — unchanged from PLAN.md §6

Django's `apps/` directory already *is* the feature-sliced structure (`accounts`, `catalog`, `orders`, `payments`, `delivery`) — one app per bounded responsibility, each with its own models/views/serializers/services. No restructuring needed; `AuthProvider` and `authenticate_or_create_google_user()` (§2 above) simply live in the existing `accounts` app:

```
api/apps/accounts/
├── models.py            # User, VendorProfile, AuthProvider
├── serializers.py
├── views.py              # RegisterView, TokenObtainPairView subclass, GoogleAuthView
├── services.py           # authenticate_or_create_google_user(), onboarding helpers
├── urls.py
└── tests/
```

### Frontend — restructured to feature-sliced

PLAN.md's original `web/app/` tree mixed routing and feature logic in the same folders. Splitting them is the one real frontend architecture change here: `app/` stays *routing-only* (thin pages that compose from `features/`), and every feature's components/hooks/API calls/types live together under `features/<name>/`. This is the standard shape for a Next.js App Router codebase past toy-app size — it's what keeps `orders`, `checkout`, and `vendor-dashboard` logic from bleeding into each other as the app grows, and it's the layout most teams hiring for this stack actually use.

```
web/
├── app/                                   # routing only — thin pages, no business logic
│   ├── (storefront)/
│   │   ├── page.tsx                       # imports from features/catalog
│   │   └── products/[slug]/page.tsx
│   ├── cart/page.tsx                      # imports from features/cart
│   ├── checkout/return/page.tsx           # imports from features/checkout
│   ├── orders/[id]/page.tsx               # imports from features/orders
│   ├── vendor/
│   │   ├── dashboard/page.tsx             # imports from features/vendor-dashboard
│   │   ├── products/page.tsx              # imports from features/vendor-products
│   │   └── onboarding/page.tsx            # imports from features/vendor-onboarding
│   ├── (auth)/
│   │   ├── login/page.tsx                 # imports from features/auth
│   │   └── register/page.tsx
│   ├── layout.tsx
│   └── middleware.ts                       # route protection (redirect if no access token)
│
├── features/
│   ├── auth/
│   │   ├── components/                    # LoginForm, RegisterForm, GoogleSignInButton
│   │   ├── hooks/                         # useAuth, useLogin, useGoogleAuth
│   │   ├── api.ts                         # login(), register(), loginWithGoogle(), refresh()
│   │   └── types.ts
│   ├── catalog/
│   │   ├── components/                    # ProductCard, ProductGrid, ProductFilters
│   │   ├── hooks/                         # useProducts, useProduct
│   │   ├── api.ts
│   │   └── types.ts
│   ├── cart/
│   │   ├── components/                    # CartDrawer, CartLineItem, VendorGroupSummary
│   │   ├── hooks/                         # useCart
│   │   ├── api.ts
│   │   └── types.ts
│   ├── checkout/
│   │   ├── components/                    # CheckoutSummary, PerVendorSessionList
│   │   ├── hooks/                         # useCheckout
│   │   └── api.ts
│   ├── orders/
│   │   ├── components/                    # OrderList, OrderDetail, DownloadButton
│   │   ├── hooks/                         # useOrders, useDownloadUrl
│   │   └── api.ts
│   ├── vendor-onboarding/
│   │   ├── components/                    # OnboardingStatusCard
│   │   ├── hooks/                         # useOnboardingStatus
│   │   └── api.ts
│   ├── vendor-products/
│   │   ├── components/                    # ProductForm, FileUploader
│   │   ├── hooks/                         # useVendorProducts, usePresignedUpload
│   │   └── api.ts
│   └── vendor-dashboard/
│       ├── components/
│       └── api.ts
│
├── components/                            # shared, feature-agnostic UI (Button, Input, Modal, Toast)
├── lib/                                   # apiClient.ts (fetch wrapper + token refresh), queryClient.ts
├── hooks/                                 # shared, non-feature hooks (useDebounce, useMediaQuery)
├── types/                                 # global/shared types (ApiError, Pagination)
├── styles/
├── public/
├── package.json
└── next.config.ts
```

**Rule of thumb for what goes where**: if a component/hook/API call is only ever used by one feature, it lives in that feature's folder. The moment two features need the same piece, it graduates to `components/`, `hooks/`, or `lib/`. `app/` files should mostly just be `return <FeatureContainer />` plus whatever Next.js requires (metadata, layout composition) — no `fetch` calls, no `useState` business logic in `app/`.

---

## 6. Trade-offs Summary

| Decision | Chosen | Rejected | Why |
|---|---|---|---|
| Google auth architecture | GIS ID token → backend verify → `simplejwt` | NextAuth.js, `django-allauth` | One token format, one source of truth; avoids the session/JWT split project already opted out of |
| Provider identity storage | Separate `AuthProvider` table | `google_sub` column on `User` | Extensible to more providers without a schema change |
| Auto-linking Google to existing password account | Allowed, gated on `email_verified` | Never auto-link / always auto-link | Blind auto-link on any email match is an account-takeover vector; refusing entirely is bad UX for the common "signed up with password, later tries Google" case |
| Frontend structure | Feature-sliced (`features/`) with thin `app/` routing | Logic inline in `app/` route folders (original PLAN.md sketch) | Matches backend's already-feature-sliced `apps/`; keeps growing feature logic from bleeding across route boundaries |

## 7. What to Revisit as This Grows

- **More providers** (GitHub, Apple) — `AuthProvider` already supports it; just add a verifier function per provider and a `provider` choice.
- **Passkeys/WebAuthn** — would sit alongside `AuthProvider` as a third auth path if pursued later; not in scope now.
- **Admin frontend** — Django Admin is fine for a single operator; a real ops team would need a dedicated internal dashboard.
- **Rate limiting on `/api/auth/google/` and `/api/auth/token/`** — not in MVP scope (see PLAN.md §7 stretch list), but the first thing to add before this is public with real traffic.
- **Cross-site refresh cookie fragility — flag for the M4 deploy milestone.** The refresh token is a cookie set by the API's origin and read only by the API; the frontend never touches it directly. That's correct by design, but PLAN.md's deploy target (Vercel for `web`, Railway for `api`) puts them on genuinely different registrable domains in production — which is exactly the shape modern browsers' third-party/cross-site cookie restrictions target. `SameSite=None; Secure` (what production uses, since `REFRESH_TOKEN_COOKIE_SAMESITE` flips off `DEBUG`) still works today in most browsers, but this is the single most likely thing to silently break a "log in, close the tab, come back tomorrow" flow after a browser update. Confirmed locally: the same class of failure reproduces even between `localhost:3000` and `localhost:8001` in a strict-cookie test setup — the access-token-in-body login/register/logout path is unaffected (works every time), but silent session restore via the refresh cookie can fail depending on browser cookie policy. **Two ways to close this before M4, worth deciding then rather than now:**
  1. Put both services under one registrable domain (`app.example.com` / `api.example.com`) so the refresh cookie is first-party, not third-party — the standard fix, but depends on owning a custom domain and wiring it to both Vercel and Railway.
  2. Accept the risk and treat a failed silent restore as "user has to log in again" (already the correct fallback behavior in `tryRestoreSession()` — it degrades to `null`, not a crash), documented in the README as a known trade-off rather than a silent bug.

---

## Build Order (delta on PLAN.md §8)

**M1** gains: `AuthProvider` model + migration, `GoogleAuthView`/`authenticate_or_create_google_user()`, `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`-equivalent env config (only the client ID is actually needed server-side for ID-token verification), frontend `features/auth/` with `GoogleSignInButton` wired to GIS. *Demo addition*: register via Google, confirm a `User` + `AuthProvider` row created with no password set; log out, log back in via Google, confirm no duplicate user; separately register the same email via password first, then sign in with Google, confirm it links to the existing account rather than erroring or duplicating.

No other milestone changes — M2–M4 stand as written in PLAN.md.
