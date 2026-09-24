# Digital Goods Marketplace

A multi-vendor marketplace for digital goods (templates, presets, ebooks, licenses) with
Stripe Connect payouts — buyers check out per-vendor, each vendor gets paid directly to
their own connected Stripe account, and the platform takes a flat fee automatically at
charge time.

Backend: Django 5 + DRF. Frontend: Next.js 16 (App Router) + TypeScript + Tailwind v4.
Payments: Stripe Connect (Express accounts, destination charges). Storage: Cloudflare R2.

See [`PLAN.md`](./PLAN.md) and [`SYSTEM_DESIGN.md`](./SYSTEM_DESIGN.md) for the full
architecture writeup — the multi-vendor cart → per-vendor `VendorSuborder` split, the
webhook idempotency ledger, the service-layer-over-signals decision, and the Google OAuth
design are all covered there. This file is the practical "how do I run/deploy this" guide.

## Local development

**Prerequisites:** Python 3.12+, Node 20+, Docker (for Postgres/Redis).

```bash
# Postgres + Redis
docker compose up -d postgres redis

# Backend
cd api
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
cp ../.env.example .env   # fill in Stripe/R2/Google credentials — see below
python manage.py migrate
python manage.py seed_demo   # optional: a few draft demo products for local browsing
python manage.py runserver 8001

# Frontend (separate terminal)
cd web
npm install
cp .env.example .env.local
npm run dev
```

Local ports are deliberately non-default (`5434` for Postgres, `6381` for Redis, `8001`
for the API) to avoid clashing with other projects' default `5432`/`6379`/`8000` on the
same machine — see the comments in `docker-compose.yml` / `.env.example` if that's not a
concern for you and you'd rather use the defaults.

### Getting a real Stripe/Google/R2 setup for local testing

- **Stripe**: create a free account, grab the test-mode secret key from the Dashboard.
  For webhooks locally, use the Stripe CLI: `stripe listen --forward-to
  localhost:8001/api/webhooks/stripe/` — it prints a `whsec_...` signing secret to put in
  `STRIPE_WEBHOOK_SECRET`.
- **Google OAuth**: see the comment in `.env.example` — you need a Web application OAuth
  client with `http://localhost:3000` as an authorized JavaScript origin. No redirect URI
  needed (see `SYSTEM_DESIGN.md` §2 for why).
- **R2**: create a bucket, an API token with Object Read & Write, and set a CORS policy on
  the bucket (browsers upload directly to R2 via presigned URLs, so R2 itself — not our
  API — needs to allow that origin):
  ```json
  [{"AllowedOrigins": ["http://localhost:3000"], "AllowedMethods": ["GET", "PUT", "HEAD"], "AllowedHeaders": ["*"], "ExposeHeaders": ["ETag"], "MaxAgeSeconds": 3600}]
  ```

### A note on Stripe Connect Express + testing

Express accounts require the *account holder* to accept Stripe's ToS through Stripe's own
hosted onboarding UI — the platform can't do this on their behalf via the API, even in
test mode. That means there's no way to script a fully "charges_enabled" vendor account
from scratch; you complete the hosted flow once per test vendor (a couple of minutes,
using Stripe's documented test-mode values — routing number `110000000`, account number
`000123456789`, SSN `000000000`, etc.). `seed_demo` deliberately does *not* fake this — see
the command's own docstring and `SYSTEM_DESIGN.md` for why faking it caused real checkout
failures for anyone who tried to buy a seeded product.

## Running tests

```bash
cd api && python manage.py test
cd web && npx eslint . && npx next build   # typecheck + lint + build
```

## Deploying

**Target layout:** `web` → Vercel, `api` (+ Celery worker) → Railway, Postgres → Railway
or Neon, Redis → Railway.

### 1. Database + Redis (Railway)

Provision a Postgres and a Redis instance on Railway (or use Neon for Postgres). Note the
connection URLs — `DATABASE_URL` and `CELERY_BROKER_URL` respectively.

### 2. API (Railway)

Deploy `api/` as a Railway service using its `Dockerfile` (Railway auto-detects it — no
extra config needed). The container's `CMD` runs migrations and `collectstatic`
automatically on every boot before starting Gunicorn, so there's no separate release step
to wire up. Railway injects `PORT`; the Dockerfile already binds to it.

Environment variables to set (see `.env.example` for the full list with comments):

| Variable | Notes |
|---|---|
| `DJANGO_SECRET_KEY` | Generate a real one — `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | Your Railway domain (e.g. `api.yourapp.up.railway.app`) |
| `DATABASE_URL` | From step 1 |
| `CELERY_BROKER_URL` | From step 1 |
| `CORS_ALLOWED_ORIGINS` | Your deployed Vercel URL |
| `FRONTEND_URL` | Same, used to build Stripe success/cancel/return URLs |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | See step 4 for the webhook secret |
| `GOOGLE_OAUTH_CLIENT_ID` | Same client as local, plus the new origin — see step 5 |
| `R2_*` | Same bucket as local, or a separate prod bucket |

Deploy the Celery worker as a second Railway service from the same repo/image, overriding
the start command to `celery -A config worker -l info` instead of the Dockerfile's default.

### 3. Web (Vercel)

Import the repo, set the root directory to `web/`. Vercel auto-detects Next.js — no build
config needed. Environment variables:

| Variable | Notes |
|---|---|
| `NEXT_PUBLIC_API_URL` | Your deployed Railway API URL |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Same as the backend's |

### 4. Stripe webhook (dashboard, not CLI, for production)

In the Stripe Dashboard (test mode is fine for a portfolio deploy) → Developers →
Webhooks → Add endpoint → `https://<your-api-domain>/api/webhooks/stripe/`, subscribed to
`checkout.session.completed`, `payment_intent.payment_failed`, `account.updated`,
`charge.refunded`. Copy the signing secret into `STRIPE_WEBHOOK_SECRET` on Railway.

### 5. Update allowlists for the production origin

Three places need the deployed frontend URL added, not just localhost:
- Google Cloud Console → the OAuth client's Authorized JavaScript origins
- R2 bucket CORS policy's `AllowedOrigins`
- `CORS_ALLOWED_ORIGINS` on the API (step 2)

### 6. Cross-site cookie caveat

The refresh-token cookie is set by the API's own origin and read only by the API — but
Vercel and Railway are different registrable domains in production, making it a
third-party cookie from the browser's perspective. Documented in detail, including the
mitigation options, in `SYSTEM_DESIGN.md` §7. Worth deciding on before or shortly after
first deploy, not before — the login/register/logout path is unaffected either way; only
"stay signed in across a closed tab" silently degrades to "log in again" if a browser
blocks it.

## Project structure

```
api/apps/{accounts,catalog,orders,payments,delivery}/   one Django app per responsibility
web/app/                                                  routing only — thin pages
web/features/{auth,catalog,cart,checkout,orders,vendor-*}/  feature logic, mirrors the backend apps
```

See `SYSTEM_DESIGN.md` §5 for the full folder-structure rationale.
