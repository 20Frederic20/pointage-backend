import asyncio
import io

from minio import Minio
from minio.error import S3Error

from core.domain.errors import NotFoundError
from core.settings import StorageSettings
from punch.application.ports import photo_key_for

__all__ = ["MinioPhotoStorage", "photo_key_for"]


class MinioPhotoStorage:
    """``IPhotoStorage`` over MinIO; the sync client runs in worker threads."""

    def __init__(self, settings: StorageSettings) -> None:
        self._bucket = settings.s3_bucket
        self._client = Minio(
            settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            secure=settings.s3_secure,
        )
        self._bucket_ready = False

    def _ensure_bucket(self) -> None:
        if self._bucket_ready:
            return
        if not self._client.bucket_exists(self._bucket):
            try:
                self._client.make_bucket(self._bucket)
            except S3Error as exc:
                if exc.code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                    raise
        self._bucket_ready = True

    def _put(self, key: str, content: bytes, content_type: str) -> None:
        self._ensure_bucket()
        self._client.put_object(
            self._bucket, key, io.BytesIO(content), len(content), content_type=content_type
        )

    def _get(self, key: str) -> tuple[bytes, str]:
        try:
            response = self._client.get_object(self._bucket, key)
        except S3Error as exc:
            if exc.code in ("NoSuchKey", "NoSuchBucket"):
                raise NotFoundError(f"Photo {key!r} not found", context=key) from exc
            raise
        try:
            return response.read(), response.headers.get("Content-Type", "application/octet-stream")
        finally:
            response.close()
            response.release_conn()

    async def put(self, key: str, content: bytes, content_type: str) -> None:
        await asyncio.to_thread(self._put, key, content, content_type)

    async def get(self, key: str) -> tuple[bytes, str]:
        return await asyncio.to_thread(self._get, key)
