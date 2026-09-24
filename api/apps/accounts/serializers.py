from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User, VendorProfile


class UserSerializer(serializers.ModelSerializer):
    has_usable_password = serializers.SerializerMethodField()
    is_vendor = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ["id", "email", "has_usable_password", "is_vendor"]

    def get_has_usable_password(self, obj: User) -> bool:
        return obj.has_usable_password()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["email", "password"]

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
        )


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Same as simplejwt's default, but the view response also includes the user object
    so the frontend doesn't need a second round trip after login.

    Also overrides simplejwt's default "no_active_account" message. That default —
    "No active account found with the given credentials" — is misleading for the (far
    more common) wrong-password case: the account does exist, only the password is wrong.
    Deliberately still one generic message for both "no such account" and "wrong password"
    (never reveal which one it was — that's a user-enumeration leak), but the wording
    itself shouldn't assert something false."""

    default_error_messages = {"no_active_account": "Invalid email or password."}

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class VendorProfileSerializer(serializers.ModelSerializer):
    # No stripe_account_id here — it's an internal reference, never returned to the client.
    # Read-only view of the profile (status endpoint) — this serializer is never used to
    # accept input, but read_only_fields is set anyway as defense-in-depth: without it,
    # charges_enabled/payouts_enabled/onboarding_status would be silently writable by
    # anyone who reused this serializer for a PATCH (see VendorProfileUpdateSerializer for
    # the one field — store_name — a vendor is actually allowed to change themselves).
    is_onboarded = serializers.ReadOnlyField()

    class Meta:
        model = VendorProfile
        fields = [
            "store_name",
            "slug",
            "onboarding_status",
            "charges_enabled",
            "payouts_enabled",
            "is_onboarded",
        ]
        read_only_fields = ["slug", "onboarding_status", "charges_enabled", "payouts_enabled"]


class VendorProfileUpdateSerializer(serializers.ModelSerializer):
    """The one vendor-editable field. Deliberately its own serializer, not a partial
    VendorProfileSerializer — keeps it structurally impossible for an update request to
    touch charges_enabled/onboarding_status/slug, even if someone widens
    VendorProfileSerializer later without noticing this endpoint reuses it."""

    class Meta:
        model = VendorProfile
        fields = ["store_name"]

    def validate_store_name(self, value):
        if (
            VendorProfile.objects.exclude(pk=self.instance.pk)
            .filter(store_name__iexact=value)
            .exists()
        ):
            raise serializers.ValidationError("That store name is already taken.")
        return value


class VendorOnboardingRequestSerializer(serializers.Serializer):
    store_name = serializers.CharField(max_length=120)
