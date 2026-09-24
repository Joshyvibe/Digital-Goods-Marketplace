from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.accounts.models import User, VendorProfile
from apps.catalog.models import Product

DEMO_VENDORS = [
    {
        "email": "studio.north@example.com",
        "store_name": "Studio North",
        "products": [
            ("Minimal Portfolio Template", "template", 2900, "A clean, typography-first portfolio template for designers."),
            ("Editorial Blog Kit", "template", 3900, "A component kit for content-heavy editorial sites."),
        ],
    },
    {
        "email": "grainlab@example.com",
        "store_name": "Grain Lab",
        "products": [
            ("Analog Film Presets", "preset", 1900, "24 Lightroom presets that emulate analog film stocks."),
            ("Moody Portrait Pack", "preset", 1500, "12 presets tuned for low-light portrait work."),
        ],
    },
    {
        "email": "founders.press@example.com",
        "store_name": "Founders Press",
        "products": [
            ("Bootstrapped: A Field Guide", "ebook", 1200, "A practical ebook on building a product without funding."),
            ("Pricing Playbook", "ebook", 900, "A short ebook on pricing strategy for indie SaaS."),
        ],
    },
]


class Command(BaseCommand):
    help = (
        "Seeds a small demo catalog: a few vendors with draft products, for local UI preview. "
        "Deliberately does NOT fake charges_enabled/payouts_enabled — a vendor can only reach "
        "that state through a real (human-completed) Stripe Express onboarding, same as any "
        "real vendor. Faking it here previously let products appear in the public catalog "
        "with no real payable Stripe account behind them, so checkout failed for anyone who "
        "tried to buy one. See SYSTEM_DESIGN.md for the follow-up."
    )

    def handle(self, *args, **options):
        for vendor_data in DEMO_VENDORS:
            user, _ = User.objects.get_or_create(
                email=vendor_data["email"], defaults={"is_active": True}
            )
            if not user.has_usable_password():
                user.set_password("demo-pass-1234")
                user.save(update_fields=["password"])

            vendor, _ = VendorProfile.objects.get_or_create(
                user=user,
                defaults={
                    "store_name": vendor_data["store_name"],
                    "slug": slugify(vendor_data["store_name"]),
                    # Honest defaults: not_started / charges_enabled=False. Only a real
                    # completed onboarding (see apps/accounts/vendor_services.py) should
                    # ever set these true.
                },
            )

            for title, category, price_cents, description in vendor_data["products"]:
                Product.objects.get_or_create(
                    vendor=vendor,
                    slug=slugify(title),
                    defaults={
                        "title": title,
                        "category": category,
                        "price_cents": price_cents,
                        "currency": "usd",
                        "description": description,
                        # Draft, not published — these vendors have no real Stripe account,
                        # so PublishedProductManager would exclude them from the public
                        # catalog anyway (vendor__charges_enabled=True); draft makes that
                        # honest rather than relying on the manager filter to hide the lie.
                        "status": "draft",
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded demo vendors and draft products (not publicly visible — no real "
                "Stripe account behind them). To see a purchasable product in the catalog, "
                "complete real Stripe Express onboarding for at least one vendor account "
                "(POST /api/vendors/onboard/, then finish the hosted flow — this is a "
                "one-time human step Stripe requires, see SYSTEM_DESIGN.md)."
            )
        )
