import io
import uuid
from pathlib import Path

from PIL import Image, ImageOps

from ..config import (
    PHOTOS_DIR,
    USE_R2,
    R2_ENDPOINT_URL,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET,
)

MAX_DIMENSION = 1600
JPEG_QUALITY = 85

_s3_client = None


def _get_s3():
    global _s3_client
    if _s3_client is None:
        import boto3

        _s3_client = boto3.client(
            "s3",
            endpoint_url=R2_ENDPOINT_URL,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )
    return _s3_client


def _compress(file_obj) -> bytes:
    """Resize + compress to JPEG in memory (quality preserved, size reduced)."""
    image = Image.open(file_obj)
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")
    image.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=JPEG_QUALITY)
    return buffer.getvalue()


def save_photo(file_obj, report_id: int) -> str:
    """Compress the uploaded image and store it. Returns a storage key."""
    data = _compress(file_obj)
    key = f"{report_id}/{uuid.uuid4().hex}.jpg"

    if USE_R2:
        _get_s3().put_object(
            Bucket=R2_BUCKET, Key=key, Body=data, ContentType="image/jpeg"
        )
        return key

    dest_path = PHOTOS_DIR / key
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(data)
    return key


def load_photo_bytes(key: str) -> bytes:
    """Return the stored image bytes (used by the PPTX generator)."""
    if USE_R2:
        obj = _get_s3().get_object(Bucket=R2_BUCKET, Key=key)
        return obj["Body"].read()
    return (PHOTOS_DIR / key).read_bytes()


def delete_photo(key: str) -> None:
    if USE_R2:
        _get_s3().delete_object(Bucket=R2_BUCKET, Key=key)
        return
    path = PHOTOS_DIR / key
    if path.exists():
        path.unlink()


def delete_report_photos(report_id: int) -> None:
    """Delete every stored photo belonging to a report."""
    if USE_R2:
        s3 = _get_s3()
        resp = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=f"{report_id}/")
        for obj in resp.get("Contents", []):
            s3.delete_object(Bucket=R2_BUCKET, Key=obj["Key"])
        return
    import shutil

    shutil.rmtree(PHOTOS_DIR / str(report_id), ignore_errors=True)
