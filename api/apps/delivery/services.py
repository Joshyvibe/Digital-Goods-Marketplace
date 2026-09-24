from django.utils import timezone

from apps.orders.models import OrderLineItem, VendorSuborder

from .models import DownloadGrant
from .r2_client import generate_presigned_get


def grant_downloads_for_suborder(suborder: VendorSuborder) -> None:
    buyer = suborder.order.buyer
    for line_item in suborder.line_items.select_related("product"):
        for product_file in line_item.product.files.all():
            DownloadGrant.objects.get_or_create(
                buyer=buyer, line_item=line_item, product_file=product_file
            )


def revoke_downloads_for_suborder(suborder: VendorSuborder) -> None:
    DownloadGrant.objects.filter(
        line_item__suborder=suborder, revoked_at__isnull=True
    ).update(revoked_at=timezone.now())


def get_downloads_for_order(order_id: int, buyer) -> list[dict]:
    # Grouped by purchased line item — not by grant — so an item with zero uploaded files
    # (a vendor data gap) still shows up with an empty file list instead of silently
    # disappearing from the buyer's view. Only paid/refunded suborders are relevant: a
    # pending or failed one was never paid for, so it has nothing to report here.
    line_items = (
        OrderLineItem.objects.filter(
            suborder__order_id=order_id,
            suborder__order__buyer=buyer,
            suborder__status__in=["paid", "refunded"],
        )
        .select_related("product", "suborder")
        .order_by("id")
    )

    results = []
    for line_item in line_items:
        grants = DownloadGrant.objects.filter(
            line_item=line_item, revoked_at__isnull=True
        ).select_related("product_file")
        results.append(
            {
                "product_title": line_item.product_title_snapshot,
                "status": line_item.suborder.status,
                "files": [
                    {
                        "filename": grant.product_file.original_filename,
                        "download_url": generate_presigned_get(grant.product_file.storage_key),
                    }
                    for grant in grants
                ],
            }
        )
    return results
