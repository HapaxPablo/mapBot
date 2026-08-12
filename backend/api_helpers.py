"""Компонент серверной части GeoMap."""

from functools import lru_cache


@lru_cache(maxsize=2)
def get_minio_client(external=False):
    """Выполняет операцию серверного компонента GeoMap."""
    from minio import Minio
    from django.conf import settings

    if external:
        endpoint = settings.MINIO_EXTERNAL_ENDPOINT
        secure = settings.MINIO_EXTERNAL_ENDPOINT_USE_HTTPS
    else:
        endpoint = settings.MINIO_ENDPOINT
        secure = settings.MINIO_USE_HTTPS

    return Minio(
        endpoint,
        region=settings.MINIO_REGION,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=secure,
        cert_check=secure,
    )
