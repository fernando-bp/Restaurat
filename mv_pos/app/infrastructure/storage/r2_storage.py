import asyncio
import uuid
from functools import partial

import boto3
from botocore.config import Config

from app.config import settings


def _get_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def _do_upload(content: bytes, key: str, content_type: str) -> None:
    client = _get_client()
    client.put_object(
        Bucket=settings.r2_bucket_name,
        Key=key,
        Body=content,
        ContentType=content_type,
    )


async def upload_image(content: bytes, filename: str, content_type: str) -> str:
    """Sube una imagen a R2 y devuelve su URL pública."""
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    key = f"images/{uuid.uuid4().hex}.{ext}"

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, partial(_do_upload, content, key, content_type))

    base = settings.r2_public_url.rstrip("/")
    return f"{base}/{key}"


def _do_delete(key: str) -> None:
    client = _get_client()
    client.delete_object(Bucket=settings.r2_bucket_name, Key=key)


async def delete_image(url: str) -> None:
    """Elimina una imagen de R2 a partir de su URL pública."""
    base = settings.r2_public_url.rstrip("/") + "/"
    if not url.startswith(base):
        return
    key = url[len(base):]
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, partial(_do_delete, key))
