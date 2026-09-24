from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-dev-only-change-me")
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Production hardening, gated on DEBUG so local dev (plain http://localhost) is unaffected.
# Railway (and most PaaS) terminate TLS at a proxy in front of the app — the app itself
# sees plain HTTP internally — so SECURE_SSL_REDIRECT needs SECURE_PROXY_SSL_HEADER too,
# or it redirect-loops forever trying to "upgrade" a request that was already HTTPS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
# Conservative starting value (1 day), not the "commit for a year" default — ratchet this
# up once the deploy is confirmed stable on HTTPS. Not preloaded: that's a much harder
# to reverse commitment and shouldn't be opted into automatically.
SECURE_HSTS_SECONDS = 86400 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    # local
    "apps.accounts",
    "apps.catalog",
    "apps.orders",
    "apps.payments",
    "apps.delivery",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
# DATABASE_URL, e.g. postgres://user:password@localhost:5432/marketplace
DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://postgres:postgres@localhost:5432/marketplace"),
}

# Auth

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files — only Django admin's own CSS/JS in this project (no other server-rendered
# templates). WhiteNoise serves these directly from the app process in production, so
# /admin/ doesn't come back unstyled on a platform with no separate static-file host.
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# DRF

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# simplejwt — access token short-lived and returned in the response body; refresh token
# lives only as an HttpOnly cookie (see apps/accounts/views.py), never in JS-reachable storage.
#
# ROTATE_REFRESH_TOKENS deliberately OFF. A rotating refresh token is single-use: the
# instant one refresh call redeems it, the old value is blacklisted, so any second request
# still holding that old cookie value 401s. That's fine when it's a browser tab racing
# itself once — the two Strict-Mode-doubled effects that motivated this in the first
# place — but it's fundamentally the wrong shape for a full page reload: the previous
# page's in-flight refresh can still be mid-flight server-side (already committed to the
# DB) at the exact moment the freshly-loaded page fires its own refresh with the same
# still-current cookie, and that one loses. Confirmed live: a plain rapid sequence of
# full reloads (no code bug, no multiple tabs) reproduced a bare 401 this way. Rotation
# across two different JS execution contexts (old page vs. new page) can't be fixed with
# an in-flight-promise guard the way same-tab races can (see lib/apiClient.ts) — there's
# no shared state to guard with. Trade-off: a stolen refresh token stays valid for its
# full lifetime instead of being cut off at next use. Logout still explicitly blacklists
# the token (see LogoutView), so revocation-on-logout is unaffected.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=10),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Namespaced, not the generic "refresh_token" — cookies are scoped by domain+path only,
# never by port, so a same-named cookie from another local project on localhost (a
# sibling portfolio project, say) would land in the exact same browser cookie jar and
# get attached to this app's requests too. Confirmed live: a stray "refresh_token"
# cookie from another project's dev server (broader path, longer max-age) was riding
# along on every request here, and depending on header parse order could shadow this
# app's own freshly-issued cookie — signature verification then fails against a token
# signed by a completely different app's SECRET_KEY, immediately after a valid login.
REFRESH_TOKEN_COOKIE_NAME = "marketplace_refresh_token"
REFRESH_TOKEN_COOKIE_SECURE = not DEBUG
REFRESH_TOKEN_COOKIE_SAMESITE = "None" if not DEBUG else "Lax"

# CORS — frontend origin(s), credentialed (cookies) requests only from these.
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"])
CORS_ALLOW_CREDENTIALS = True

# Google OAuth (ID token verification — see apps/accounts/services.py)
GOOGLE_OAUTH_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID", default="")

# Stripe
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")
PLATFORM_FEE_RATE = env.float("PLATFORM_FEE_RATE", default=0.15)

# Cloudflare R2 (S3-compatible) — object storage for product files
R2_ACCOUNT_ID = env("R2_ACCOUNT_ID", default="")
R2_ACCESS_KEY_ID = env("R2_ACCESS_KEY_ID", default="")
R2_SECRET_ACCESS_KEY = env("R2_SECRET_ACCESS_KEY", default="")
R2_BUCKET_NAME = env("R2_BUCKET_NAME", default="marketplace-dev")
R2_ENDPOINT_URL = env("R2_ENDPOINT_URL", default="")

# Celery
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")
