import stripe

from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

__all__ = ["stripe"]
