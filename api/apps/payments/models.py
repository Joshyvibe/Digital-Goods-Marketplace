from django.db import models


class StripeWebhookEvent(models.Model):
    # Idempotency ledger — the whole retry-safety story keys off this table.
    STATUS_CHOICES = [
        ("received", "Received"),
        ("processed", "Processed"),
        ("failed", "Failed"),
        ("ignored", "Ignored"),
    ]

    stripe_event_id = models.CharField(max_length=128, unique=True)  # evt_...
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="received")
    error_message = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.event_type} ({self.stripe_event_id})"
