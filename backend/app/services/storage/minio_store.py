from __future__ import annotations

from io import BytesIO

from minio import Minio

from app.core.config import get_settings


class MinioStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = Minio(
            endpoint=self.settings.minio_endpoint,
            access_key=self.settings.minio_access_key,
            secret_key=self.settings.minio_secret_key,
            secure=self.settings.minio_secure,
        )

    def _ensure_bucket(self) -> None:
        bucket = self.settings.minio_bucket
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)
        # Read-only anonymous policy for local development preview/download flows.
        self._client.set_bucket_policy(
            bucket,
            (
                '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":["*"]},'
                '"Action":["s3:GetBucketLocation","s3:ListBucket"],"Resource":["arn:aws:s3:::%s"]},'
                '{"Effect":"Allow","Principal":{"AWS":["*"]},"Action":["s3:GetObject"],'
                '"Resource":["arn:aws:s3:::%s/*"]}]}'
            )
            % (bucket, bucket),
        )

    def upload_bytes(self, object_key: str, content: bytes, content_type: str) -> str:
        self._ensure_bucket()
        self._client.put_object(
            bucket_name=self.settings.minio_bucket,
            object_name=object_key,
            data=BytesIO(content),
            length=len(content),
            content_type=content_type or "application/octet-stream",
        )
        return f"{self.settings.minio_public_base_url.rstrip('/')}/{self.settings.minio_bucket}/{object_key}"


MINIO_STORE = MinioStore()
