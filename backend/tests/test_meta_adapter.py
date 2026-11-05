import json
import sys
from types import SimpleNamespace

import pytest

from adapters.meta_vision import MetaVisionAdapter, MetaVisionError
from config import Settings
from models import Annotation, MuscleRegion, PixelPoint, Point


def settings(tmp_path):
    return Settings(
        storage_dir=tmp_path,
        cors_origins=("http://localhost:3000",),
        meta_api_enabled=True,
        model_api_key="server-secret",
        model_api_base_url="https://api.meta.ai/v1",
        model_api_model="muse-spark-1.3",
        meta_api_timeout_seconds=5,
        meta_api_total_limit=1,
    )


def region(name, display, group, side):
    return MuscleRegion(
        name=name, display_name=display, group=group, side=side,
        annotation=Annotation(
            normalized_points=[Point(x=.4, y=.2), Point(x=.6, y=.2), Point(x=.5, y=.4)],
            pixel_points=[PixelPoint(x=40, y=20), PixelPoint(x=60, y=20), PixelPoint(x=50, y=40)],
            label_anchor=Point(x=.5, y=.3), label_position=Point(x=.1, y=.3),
        ),
    )


def test_sdk_uses_official_meta_endpoint_without_retries(tmp_path, monkeypatch):
    captured = {}
    class FakeOpenAI:
        def __init__(self, **kwargs): captured.update(kwargs)
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))
    MetaVisionAdapter(settings(tmp_path))
    assert captured == {
        "api_key": "server-secret", "base_url": "https://api.meta.ai/v1",
        "timeout": 5, "max_retries": 0,
    }


def test_identification_sends_front_then_back_in_exactly_one_request(tmp_path):
    calls = []
    front_region = region("left_pectoralis_major", "Left pectoralis major", "chest", "left")
    back_region = region("trapezius", "Trapezius", "back", "centre")
    class FakeResponses:
        def create(self, **body):
            calls.append(body)
            content = body["input"][0]["content"]
            assert [item["type"] for item in content] == ["input_text", "input_image", "input_image"]
            assert "FIRST image is the FRONT" in content[0]["text"]
            assert "0-1000 grid" in content[0]["text"]
            assert "SUBJECT'S left and right" in content[0]["text"]
            assert "boundary_points" in content[0]["text"]
            assert "grounding_box" in content[0]["text"]
            assert content[1]["image_url"] != content[2]["image_url"]
            assert body["text"]["format"]["strict"] is True
            output = json.dumps({
                "front_view": "front", "back_view": "back",
                "muscles": [
                    {"muscle_name": front_region.name, "view": "front", "location_quality": "visible_surface", "observation": "Visible chest region.", "grounding_point": {"x": 500, "y": 300}, "grounding_box": {"x_min": 400, "y_min": 200, "x_max": 600, "y_max": 400}, "boundary_points": [{"x": 400, "y": 300}, {"x": 500, "y": 200}, {"x": 600, "y": 300}, {"x": 500, "y": 400}]},
                    {"muscle_name": back_region.name, "view": "back", "location_quality": "estimated_deep", "observation": "Approximate upper-back location.", "grounding_point": {"x": 500, "y": 250}, "grounding_box": None, "boundary_points": []},
                ],
                "warnings": [],
            })
            return SimpleNamespace(output_text=output, model_dump=lambda **kwargs: {"id": "identification"})
    adapter = MetaVisionAdapter(settings(tmp_path), SimpleNamespace(responses=FakeResponses()))
    result, _ = adapter.identify_pair(b"front", b"back", [front_region], [back_region])
    assert result.front_view == "front" and result.back_view == "back"
    assert len(calls) == 1


def test_malformed_or_missing_candidate_fails_without_retry(tmp_path):
    count = 0
    class FakeResponses:
        def create(self, **body):
            nonlocal count
            count += 1
            output = json.dumps({"front_view": "front", "back_view": "back", "muscles": [], "warnings": []})
            return SimpleNamespace(output_text=output, model_dump=lambda **kwargs: {})
    adapter = MetaVisionAdapter(settings(tmp_path), SimpleNamespace(responses=FakeResponses()))
    with pytest.raises(MetaVisionError):
        adapter.identify_pair(
            b"front", b"back",
            [region("left_pectoralis_major", "Left pectoralis major", "chest", "left")], [],
        )
    assert count == 1
