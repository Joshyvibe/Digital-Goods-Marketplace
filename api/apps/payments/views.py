from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.payments.stripe_client import stripe

from .models import StripeWebhookEvent
from .services import HANDLERS


class StripeWebhookView(APIView):
    """No auth decorator — signature verification *is* the auth. parser_classes=[] keeps
    DRF from consuming the body before we read the raw bytes construct_event needs."""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    parser_classes = []

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
        except (ValueError, stripe.SignatureVerificationError):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Idempotency: Stripe redelivers on retries/manual redelivery. If this event id was
        # already recorded, it's a no-op — no reprocessing, no double side effects.
        webhook_event, created = StripeWebhookEvent.objects.get_or_create(
            stripe_event_id=event["id"],
            defaults={"event_type": event["type"], "payload": event.to_dict()},
        )
        if not created:
            return Response(status=status.HTTP_200_OK)

        handler = HANDLERS.get(event["type"])
        if handler is None:
            webhook_event.status = "ignored"
            webhook_event.processed_at = timezone.now()
            webhook_event.save(update_fields=["status", "processed_at"])
            return Response(status=status.HTTP_200_OK)

        try:
            with transaction.atomic():
                handler(event)
        except Exception as exc:
            webhook_event.status = "failed"
            webhook_event.error_message = str(exc)
            webhook_event.save(update_fields=["status", "error_message"])
            # Re-raise -> 5xx. Swallowing this would silently lose the event forever; a
            # 5xx is what makes Stripe's retry schedule actually fire.
            raise

        webhook_event.status = "processed"
        webhook_event.processed_at = timezone.now()
        webhook_event.save(update_fields=["status", "processed_at"])
        return Response(status=status.HTTP_200_OK)
