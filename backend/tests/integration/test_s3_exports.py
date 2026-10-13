"""S3 adapter against an owned local object server, never a configured user bucket."""

import asyncio
import subprocess
import time
from pathlib import Path
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from scope_guard.integrations.storage.s3 import S3ObjectStorage

pytestmark = pytest.mark.integration


def test_conditional_s3_upload_and_storage_restart():
    token = uuid4().hex
    name = "scg-s3-test-" + token

    def docker(*args):
        return subprocess.run(
            ["docker", *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    root = Path(__file__).resolve().parents[3]
    image = "scope-guard-s3-test:release20250422"
    docker(
        "build",
        "-f",
        str(Path(__file__).with_name("storage-server.Dockerfile")),
        "-t",
        image,
        str(root),
    )
    identifier = docker(
        "run",
        "--rm",
        "-d",
        "--name",
        name,
        "--label",
        "scope-guard.disposable=" + token,
        "-e",
        "MINIO_ROOT_USER=scg_test",
        "-e",
        "MINIO_ROOT_PASSWORD=" + token,
        "-p",
        "127.0.0.1::9000",
        image,
        "server",
        "/data",
    )
    try:
        port = docker("port", identifier, "9000/tcp").rsplit(":", 1)[1]
        parameters = {
            "endpoint": "http://127.0.0.1:" + port,
            "access_key": "scg_test",
            "secret_key": token,
        }
        bucket = "scg-test-" + token
        storage = S3ObjectStorage(bucket, **parameters)
        for attempt in range(60):
            try:
                storage.client.create_bucket(Bucket=bucket)
                break
            except Exception:
                if attempt == 59:
                    raise
                time.sleep(0.5)

        async def exercise():
            await storage.put("exports/example/1.pdf", b"saved PDF bytes")
            with pytest.raises(ClientError):
                await storage.put("exports/example/1.pdf", b"must not overwrite")
            assert (
                await S3ObjectStorage(bucket, **parameters).get("exports/example/1.pdf")
                == b"saved PDF bytes"
            )

        asyncio.run(exercise())
        docker("restart", identifier)
        # Docker may allocate a different anonymous host port when the server restarts.
        port = docker("port", identifier, "9000/tcp").rsplit(":", 1)[1]
        parameters["endpoint"] = "http://127.0.0.1:" + port
        for attempt in range(60):
            try:
                assert (
                    asyncio.run(S3ObjectStorage(bucket, **parameters).get("exports/example/1.pdf"))
                    == b"saved PDF bytes"
                )
                break
            except Exception:
                if attempt == 59:
                    raise
                time.sleep(0.5)
    finally:
        label = docker(
            "inspect", "--format", '{{index .Config.Labels "scope-guard.disposable"}}', identifier
        )
        if label != token:
            raise RuntimeError("Disposable storage ownership mismatch")
        docker("rm", "-f", identifier)
