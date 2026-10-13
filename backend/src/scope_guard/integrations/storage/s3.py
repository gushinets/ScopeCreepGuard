"""Private S3-compatible storage with conditional uploads and bounded downloads."""

import asyncio
import base64
import hashlib


class S3ObjectStorage:
    def __init__(
        self, bucket: str, *, endpoint=None, region="us-east-1", access_key=None, secret_key=None
    ):
        import boto3
        from botocore.config import Config

        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(connect_timeout=5, read_timeout=30, retries={"max_attempts": 2}),
        )

    async def put(self, key: str, data: bytes) -> None:
        await asyncio.to_thread(
            self.client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType="application/pdf",
            IfNoneMatch="*",
            ChecksumSHA256=base64.b64encode(hashlib.sha256(data).digest()).decode(),
        )

    async def get(self, key: str) -> bytes:
        def read():
            result = self.client.get_object(Bucket=self.bucket, Key=key)
            body = result["Body"]
            try:
                data = body.read(16 * 1024 * 1024 + 1)
                if len(data) > 16 * 1024 * 1024:
                    raise ValueError("export_too_large")
                return data
            finally:
                body.close()

        return await asyncio.to_thread(read)

    async def list(self) -> list[dict]:
        def objects():
            return [
                {"key": item["Key"], "createdAt": item["LastModified"]}
                for page in self.client.get_paginator("list_objects_v2").paginate(
                    Bucket=self.bucket, Prefix="exports/scg-"
                )
                for item in page.get("Contents", [])
            ]

        return await asyncio.to_thread(objects)

    async def remove(self, key: str) -> None:
        await asyncio.to_thread(self.client.delete_object, Bucket=self.bucket, Key=key)
