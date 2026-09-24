from django.contrib import admin

from .models import StripeWebhookEvent


@admin.register(StripeWebhookEvent)
class StripeWebhookEventAdmin(admin.ModelAdmin):
    list_display = ["stripe_event_id", "event_type", "status", "received_at", "processed_at"]
    list_filter = ["status", "event_type"]
    readonly_fields = ["payload"]
