from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from django.conf import settings

from . import services, vendor_services
from .models import User
from .serializers import (
    CustomTokenObtainPairSerializer,
    GoogleAuthSerializer,
    RegisterSerializer,
    UserSerializer,
    VendorOnboardingRequestSerializer,
    VendorProfileSerializer,
    VendorProfileUpdateSerializer,
)
from .services import GoogleAuthError
from .vendor_services import VendorOnboardingError


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        access, refresh = services.issue_token_pair(user)
        response = Response(
            {"access": access, "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )
        services.set_refresh_cookie(response, refresh)
        return response


class CustomTokenObtainPairView(TokenObtainPairView):
    """Email/password login. Returns the access token + user in the body; the refresh
    token is set as an HttpOnly cookie, never exposed to JS (see services.set_refresh_cookie)."""

    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        refresh = data.pop("refresh")
        response = Response(data, status=status.HTTP_200_OK)
        services.set_refresh_cookie(response, str(refresh))
        return response


class CookieTokenRefreshView(APIView):
    """Reads the refresh token from the HttpOnly cookie (never the request body) and
    issues a new access token. Rotation is on (SIMPLE_JWT.ROTATE_REFRESH_TOKENS), so the
    cookie is replaced with a new refresh token on every call and the old one is blacklisted."""

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        raw_refresh = request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME)
        if not raw_refresh:
            return Response({"detail": "No refresh token."}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = TokenRefreshSerializer(data={"refresh": raw_refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except (InvalidToken, TokenError):
            response = Response({"detail": "Invalid refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
            services.clear_refresh_cookie(response)
            return response

        data = serializer.validated_data
        new_refresh = data.pop("refresh", raw_refresh)

        response = Response(data, status=status.HTTP_200_OK)
        services.set_refresh_cookie(response, str(new_refresh))
        return response


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        raw_refresh = request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME)
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except TokenError:
                pass  # already invalid/expired — logout should still succeed

        response = Response(status=status.HTTP_204_NO_CONTENT)
        services.clear_refresh_cookie(response)
        return response


class GoogleAuthView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = services.authenticate_or_create_google_user(
                serializer.validated_data["id_token"]
            )
        except GoogleAuthError:
            return Response(
                {"detail": "Google sign-in failed."}, status=status.HTTP_401_UNAUTHORIZED
            )

        access, refresh = services.issue_token_pair(user)
        response = Response({"access": access, "user": UserSerializer(user).data})
        services.set_refresh_cookie(response, refresh)
        return response


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(UserSerializer(request.user).data)

    def delete(self, request, *args, **kwargs):
        outcome = services.delete_or_deactivate_account(request.user)

        response = Response({"outcome": outcome}, status=status.HTTP_200_OK)
        services.clear_refresh_cookie(response)
        return response


class VendorOnboardingView(APIView):
    """POST /api/vendors/onboard — creates the VendorProfile and Stripe Express account on
    first call (idempotent after that), and always returns a fresh AccountLink URL to
    redirect into. A vendor can call this again later to resume/redo onboarding."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = VendorOnboardingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            vendor = vendor_services.get_or_create_vendor_profile(
                request.user, serializer.validated_data["store_name"]
            )
            vendor = vendor_services.ensure_stripe_account(vendor)
            onboarding_url = vendor_services.create_onboarding_link(vendor)
        except VendorOnboardingError:
            return Response(
                {"detail": "Could not start vendor onboarding. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"onboarding_url": onboarding_url})


class VendorOnboardingStatusView(APIView):
    """GET /api/vendors/onboarding-status — the return-URL page calls this rather than
    trusting the redirect itself as proof of completion (see vendor_services docstring)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if not hasattr(request.user, "vendor_profile"):
            return Response({"detail": "Not a vendor yet."}, status=status.HTTP_404_NOT_FOUND)

        vendor = request.user.vendor_profile
        try:
            vendor_services.sync_onboarding_status(vendor)
        except VendorOnboardingError:
            pass  # serve last-known-good status rather than fail the page on a Stripe hiccup

        return Response(VendorProfileSerializer(vendor).data)

    def patch(self, request, *args, **kwargs):
        if not hasattr(request.user, "vendor_profile"):
            return Response({"detail": "Not a vendor yet."}, status=status.HTTP_404_NOT_FOUND)

        serializer = VendorProfileUpdateSerializer(
            request.user.vendor_profile, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(VendorProfileSerializer(request.user.vendor_profile).data)
