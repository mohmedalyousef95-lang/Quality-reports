import uuid
from pathlib import Path

from PIL import Image, ImageOps

from ..config import PHOTOS_DIR

MAX_DIMENSION = 1600
JPEG_QUALITY = 85


def save_photo(file_obj, report_id: int) -> Path:
    dest_dir = PHOTOS_DIR / str(report_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{uuid.uuid4().hex}.jpg"

    image = Image.open(file_obj)
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")
    image.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
    image.save(dest_path, "JPEG", quality=JPEG_QUALITY)
    return dest_path


def delete_photo_file(file_path: str) -> None:
    path = Path(file_path)
    if path.exists():
        path.unlink()
