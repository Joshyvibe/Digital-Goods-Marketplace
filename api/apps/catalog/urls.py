from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PublicProductViewSet, VendorProductViewSet, VendorStorefrontView

router = DefaultRouter()
router.register("products", PublicProductViewSet, basename="product")
router.register("vendors/products", VendorProductViewSet, basename="vendor-product")

urlpatterns = router.urls + [
    path("store/<slug:slug>/", VendorStorefrontView.as_view(), name="vendor-storefront"),
]
