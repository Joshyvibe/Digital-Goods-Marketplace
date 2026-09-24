from django.urls import path

from . import views

urlpatterns = [
    path("onboard/", views.VendorOnboardingView.as_view(), name="vendor-onboard"),
    path(
        "onboarding-status/",
        views.VendorOnboardingStatusView.as_view(),
        name="vendor-onboarding-status",
    ),
]
