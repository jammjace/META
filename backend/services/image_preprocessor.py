from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageOps


class InvalidImageError(ValueError):
    pass


@dataclass(frozen=True)
class PreparedImage:
    original_jpeg: bytes
    inference_jpeg: bytes
    width: int
    height: int


def prepare_image(payload: bytes, max_bytes: int = 12 * 1024 * 1024) -> PreparedImage:
    if not payload or len(payload) > max_bytes:
        raise InvalidImageError("Photo must be between 1 byte and 12 MB.")
    try:
        with Image.open(io.BytesIO(payload)) as source:
            source.verify()
        with Image.open(io.BytesIO(payload)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
    except Exception as exc:
        raise InvalidImageError("The uploaded file is not a decodable image.") from exc
    width, height = image.size
    if width < 320 or height < 320:
        raise InvalidImageError("Photo dimensions must be at least 320 by 320 pixels.")
    original = io.BytesIO()
    image.save(original, format="JPEG", quality=94, optimize=True)
    inference = image.copy()
    inference.thumbnail((1536, 1536), Image.Resampling.LANCZOS)
    normalized = io.BytesIO()
    inference.save(normalized, format="JPEG", quality=88, optimize=True)
    return PreparedImage(original.getvalue(), normalized.getvalue(), width, height)

