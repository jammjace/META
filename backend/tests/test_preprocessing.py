import pytest

from services.image_preprocessor import InvalidImageError, prepare_image


def test_prepares_real_image(photo_bytes):
    result = prepare_image(photo_bytes)
    assert (result.width, result.height) == (800, 1000)
    assert result.original_jpeg.startswith(b"\xff\xd8")
    assert result.inference_jpeg.startswith(b"\xff\xd8")


def test_rejects_invalid_image():
    with pytest.raises(InvalidImageError):
        prepare_image(b"not an image")

