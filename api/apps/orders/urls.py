from django.urls import path

from . import views

urlpatterns = [
    path("cart/", views.CartView.as_view(), name="cart"),
    path("cart/items/", views.CartItemView.as_view(), name="cart-items"),
    path("cart/items/<int:product_id>/", views.CartItemView.as_view(), name="cart-item-detail"),
    path("orders/checkout/", views.CheckoutView.as_view(), name="checkout"),
    path("orders/", views.OrderListView.as_view(), name="order-list"),
    path("orders/<int:pk>/", views.OrderDetailView.as_view(), name="order-detail"),
    path(
        "orders/<int:order_id>/suborders/<int:suborder_id>/retry/",
        views.SuborderRetryView.as_view(),
        name="suborder-retry",
    ),
    path(
        "orders/<int:order_id>/suborders/<int:suborder_id>/",
        views.SuborderCancelView.as_view(),
        name="suborder-cancel",
    ),
    path("vendors/sales/", views.VendorSalesView.as_view(), name="vendor-sales"),
]
