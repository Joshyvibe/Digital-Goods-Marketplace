from django.db import models

from apps.accounts.models import User
from apps.orders.models import OrderLineItem


class DownloadGrant(models.Model):
    # Permanent proof-of-purchase, created once at checkout.session.completed. Signed URLs
    # are disposable and regenerated on demand from this grant — see PLAN.md §3.
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="download_grants")
    line_item = models.ForeignKey(OrderLineItem, on_delete=models.CASCADE, related_name="download_grants")
    product_file = models.ForeignKey(
        "catalog.ProductFile", on_delete=models.CASCADE, related_name="download_grants"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["line_item", "product_file"], name="uniq_grant_per_line_item_file"
            )
        ]

    def __str__(self):
        return f"DownloadGrant(buyer={self.buyer_id}, file={self.product_file_id})"
