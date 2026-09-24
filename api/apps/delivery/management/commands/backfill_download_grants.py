from django.core.management.base import BaseCommand

from apps.delivery.services import grant_downloads_for_suborder
from apps.orders.models import VendorSuborder


class Command(BaseCommand):
    help = "Create DownloadGrants for already-paid suborders that predate the delivery app."

    def handle(self, *args, **options):
        suborders = VendorSuborder.objects.filter(status="paid")
        for suborder in suborders:
            grant_downloads_for_suborder(suborder)
        self.stdout.write(self.style.SUCCESS(f"Backfilled grants for {suborders.count()} paid suborder(s)."))
