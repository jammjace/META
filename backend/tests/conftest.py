from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def photo_bytes() -> bytes:
    image = Image.new("RGB", (800, 1000), (80, 88, 98))
    output = io.BytesIO()
    image.save(output, "JPEG")
    return output.getvalue()

