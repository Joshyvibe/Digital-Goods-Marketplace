from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    # Email-as-username; no separate Buyer/Vendor tables — VendorProfile is an additive
    # role on the same identity (see SYSTEM_DESIGN.md §1 / PLAN.md §1).
    username = None
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def is_vendor(self) -> bool:
        return hasattr(self, "vendor_profile")


class VendorProfile(models.Model):
    ONBOARDING_STATUS_CHOICES = [
        ("not_started", "Not Started"),
        ("pending", "Pending"),
        ("complete", "Complete"),
        ("restricted", "Restricted"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="vendor_profile")
    store_name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(unique=True)
    stripe_account_id = models.CharField(max_length=64, blank=True)
    onboarding_status = models.CharField(
        max_length=20, choices=ONBOARDING_STATUS_CHOICES, default="not_started"
    )
    charges_enabled = models.BooleanField(default=False)
    payouts_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_onboarded(self) -> bool:
        return self.charges_enabled and self.payouts_enabled

    def __str__(self):
        return self.store_name


class AuthProvider(models.Model):
    # Links a User to an external identity provider. Password-only users have zero rows
    # here. Kept as a separate table (not a column on User) so adding GitHub/Apple later
    # needs no schema change — see SYSTEM_DESIGN.md §2.2.
    PROVIDER_CHOICES = [
        ("google", "Google"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="auth_providers")
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=255)  # e.g. Google's `sub` claim
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_user_id"], name="uniq_provider_account"
            )
        ]

    def __str__(self):
        return f"{self.provider}:{self.provider_user_id}"
