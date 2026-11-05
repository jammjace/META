import io

import pytest
from PIL import Image

from services.image_preprocessor import InvalidImageError, prepare_image


def test_prepares_real_image(photo_bytes):
    result = prepare_image(photo_bytes)
    assert (result.width, result.height) == (800, 1000)
    assert result.original_jpeg.startswith(b"\xff\xd8")
    assert result.inference_jpeg.startswith(b"\xff\xd8")
    assert Image.open(io.BytesIO(result.inference_jpeg)).size == (1000, 1000)
    assert result.transform.source_to_inference(0, 0) == pytest.approx((.1, 0))
    assert result.transform.inference_to_source(.1, 0) == pytest.approx((0, 0))
    assert result.transform.inference_to_source(.9, 1) == pytest.approx((1, 1))


def test_rejects_invalid_image():
    with pytest.raises(InvalidImageError):
        prepare_image(b"not an image")

