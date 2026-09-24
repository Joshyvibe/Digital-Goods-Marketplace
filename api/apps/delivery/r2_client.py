from urllib.parse import urlsplit, urlunsplit

import boto3
from botocore.config import Config

from django.conf import settings


class R2NotConfiguredError(Exception):
    """Raised when R2 credentials/endpoint are missing — lets callers return a clean 502
    instead of a raw boto3 stack trace."""


def _bare_endpoint(url: str) -> str:
    """R2's dashboard sometimes shows the endpoint with the bucket name appended
    (.../<account_id>.r2.cloudflarestorage.com/<bucket>) — boto3 wants just scheme+host,
    the bucket is a separate parameter on every call. Strip any path component."""
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def _client():
    if not (settings.R2_ENDPOINT_URL and settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY):
        raise R2NotConfiguredError("R2 credentials are not configured")

    return boto3.client(
        "s3",
        endpoint_url=_bare_endpoint(settings.R2_ENDPOINT_URL),
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def generate_presigned_put(key: str, content_type: str, expires_in: int = 600) -> str:
    return _client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.R2_BUCKET_NAME, "Key": key, "ContentType": content_type},
        ExpiresIn=expires_in,
    )


def generate_presigned_get(key: str, expires_in: int = 600) -> str:
    """10 minutes by default — long enough to complete a download, short enough that a
    leaked link is quickly worthless (see SYSTEM_DESIGN.md delivery mechanism, M3)."""
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.R2_BUCKET_NAME, "Key": key},
        ExpiresIn=expires_in,
    )
