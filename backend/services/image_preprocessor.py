from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageOps


class InvalidImageError(ValueError):
    pass


@dataclass(frozen=True)
class ImageTransform:
    """Mapping between the EXIF-corrected source and square inference canvas."""

    source_width: int
    source_height: int
    inference_width: int
    inference_height: int
    scaled_width: int
    scaled_height: int
    offset_x: int
    offset_y: int

    def inference_to_source(self, x: float, y: float) -> tuple[float, float]:
        pixel_x = x * self.inference_width
        pixel_y = y * self.inference_height
        return (
            (pixel_x - self.offset_x) / self.scaled_width,
            (pixel_y - self.offset_y) / self.scaled_height,
        )

    def source_to_inference(self, x: float, y: float) -> tuple[float, float]:
        return (
            (self.offset_x + x * self.scaled_width) / self.inference_width,
            (self.offset_y + y * self.scaled_height) / self.inference_height,
        )


@dataclass(frozen=True)
class PreparedImage:
    original_jpeg: bytes
    inference_jpeg: bytes
    width: int
    height: int
    transform: ImageTransform


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
    canvas_size = min(1536, max(width, height))
    scale = min(canvas_size / width, canvas_size / height)
    scaled_width = max(1, round(width * scale))
    scaled_height = max(1, round(height * scale))
    resized = image.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
    offset_x = (canvas_size - scaled_width) // 2
    offset_y = (canvas_size - scaled_height) // 2
    inference = Image.new("RGB", (canvas_size, canvas_size), (24, 24, 24))
    inference.paste(resized, (offset_x, offset_y))
    normalized = io.BytesIO()
    inference.save(normalized, format="JPEG", quality=88, optimize=True)
    transform = ImageTransform(
        source_width=width,
        source_height=height,
        inference_width=canvas_size,
        inference_height=canvas_size,
        scaled_width=scaled_width,
        scaled_height=scaled_height,
        offset_x=offset_x,
        offset_y=offset_y,
    )
    return PreparedImage(original.getvalue(), normalized.getvalue(), width, height, transform)

