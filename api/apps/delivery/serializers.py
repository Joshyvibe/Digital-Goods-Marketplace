from rest_framework import serializers


class DownloadFileSerializer(serializers.Serializer):
    filename = serializers.CharField()
    download_url = serializers.URLField()


class DownloadItemSerializer(serializers.Serializer):
    product_title = serializers.CharField()
    status = serializers.CharField()
    files = DownloadFileSerializer(many=True)
