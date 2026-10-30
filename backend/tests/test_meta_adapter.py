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


def region():
    return MuscleRegion(
        name="trapezius", display_name="Trapezius", group="trapezius", side="centre",
        annotation=Annotation(
            normalized_points=[Point(x=.4, y=.2), Point(x=.6, y=.2), Point(x=.5, y=.4)],
            pixel_points=[PixelPoint(x=40, y=20), PixelPoint(x=60, y=20), PixelPoint(x=50, y=40)],
            label_anchor=Point(x=.5, y=.3),
            label_position=Point(x=.1, y=.3),
        ),
    )


def test_one_request_contains_image_and_all_muscles(tmp_path):
    calls = []
    class FakeResponses:
      def create(self, **body):
        calls.append(body)
        assert body["model"] == "muse-spark-1.3"
        assert body["input"][0]["content"][0]["type"] == "input_text"
        image = body["input"][0]["content"][1]
        assert image["type"] == "input_image"
        assert image["image_url"].startswith("data:image/jpeg;base64,")
        assert body["text"]["format"]["type"] == "json_schema"
        assert body["text"]["format"]["strict"] is True
        content = json.dumps({
            "view": "back",
            "observations": [{"muscle_name": "trapezius", "observation": "Visible upper-back contour.", "visible": True}],
        })
        return SimpleNamespace(
            output_text=content,
            model_dump=lambda **kwargs: {"id": "response_test", "output_text": content},
        )
    client = SimpleNamespace(responses=FakeResponses())
    adapter = MetaVisionAdapter(settings(tmp_path), client=client)
    result, _ = adapter.analyze(b"jpeg", [region()])
    assert result.view == "back"
    assert len(calls) == 1


def test_official_sdk_is_configured_for_meta_responses_without_retries(tmp_path, monkeypatch):
    captured = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))
    MetaVisionAdapter(settings(tmp_path))

    assert captured == {
        "api_key": "server-secret",
        "base_url": "https://api.meta.ai/v1",
        "timeout": 5,
        "max_retries": 0,
    }


def test_failure_is_not_retried(tmp_path):
    count = 0
    class FailingResponses:
      def create(self, **kwargs):
        nonlocal count
        count += 1
        raise RuntimeError("provider failed")
    adapter = MetaVisionAdapter(
        settings(tmp_path), SimpleNamespace(responses=FailingResponses())
    )
    with pytest.raises(MetaVisionError):
        adapter.analyze(b"jpeg", [region()])
    assert count == 1


def test_comparison_sends_two_ordered_images_in_one_response_request(tmp_path):
    calls = []
    class FakeResponses:
        def create(self, **body):
            calls.append(body)
            content = body["input"][0]["content"]
            assert [item["type"] for item in content] == ["input_text", "input_image", "input_image"]
            assert "FIRST image is the BASELINE" in content[0]["text"]
            assert content[1]["image_url"] != content[2]["image_url"]
            assert body["text"]["format"]["strict"] is True
            output = json.dumps({
                "baseline_view": "back", "current_view": "back",
                "overall_summary": "No clear overall visible change.",
                "muscle_progress": [{
                    "muscle": "trapezius", "status": "no_clear_change",
                    "observation": "The visible contour appears similar.", "limitation": None,
                }],
                "comparison_warnings": [],
            })
            return SimpleNamespace(
                output_text=output,
                model_dump=lambda **kwargs: {"id": "comparison_response"},
            )
    adapter = MetaVisionAdapter(settings(tmp_path), SimpleNamespace(responses=FakeResponses()))
    result, _ = adapter.compare(b"baseline", b"current", [region()], [])
    assert result.muscle_progress[0].muscle == "trapezius"
    assert len(calls) == 1


def test_malformed_comparison_response_fails_without_retry(tmp_path):
    count = 0
    class FakeResponses:
        def create(self, **body):
            nonlocal count
            count += 1
            return SimpleNamespace(output_text='{"wrong":true}', model_dump=lambda **kwargs: {})
    adapter = MetaVisionAdapter(settings(tmp_path), SimpleNamespace(responses=FakeResponses()))
    with pytest.raises(MetaVisionError):
        adapter.compare(b"baseline", b"current", [region()], [])
    assert count == 1

