from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order

from .serializers import DownloadItemSerializer
from .services import get_downloads_for_order


class DownloadListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, order_id, *args, **kwargs):
        if not Order.objects.filter(id=order_id, buyer=request.user).exists():
            return Response({"detail": "Order not found."}, status=404)

        downloads = get_downloads_for_order(order_id, request.user)
        return Response(DownloadItemSerializer(downloads, many=True).data)
