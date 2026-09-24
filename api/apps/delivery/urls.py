from django.urls import path

from . import views

urlpatterns = [
    path("orders/<int:order_id>/downloads/", views.DownloadListView.as_view(), name="order-downloads"),
]
