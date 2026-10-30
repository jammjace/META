from fastapi.testclient import TestClient

import app as app_module
from app import app

client = TestClient(app)


def test_comparison_requires_both_files():
    response = client.post("/api/comparisons")
    assert response.status_code == 422


def test_comparison_rejects_non_images_before_pipeline():
    response = client.post("/api/comparisons", files={
        "baseline": ("before.txt", b"before", "text/plain"),
        "current": ("now.txt", b"now", "text/plain"),
    })
    assert response.status_code == 415


def test_successful_two_photo_upload_preserves_baseline_current_order(monkeypatch):
    class FakePipeline:
        received = None
        def process(self, baseline, current):
            self.received = (baseline, current)
            return {
                "comparison_id": "b" * 32,
                "status": "complete",
                "baseline": {"image": {"width": 800, "height": 1000, "url": "/before"}, "view": "back", "annotations": []},
                "current": {"image": {"width": 800, "height": 1000, "url": "/now"}, "view": "back", "annotations": []},
                "overall_summary": "No clear overall visible change.",
                "muscle_progress": [],
                "comparison_warnings": [],
                "model": {"provider": "meta", "name": "muse-spark-1.3"},
            }
    pipeline = FakePipeline()
    monkeypatch.setattr(app_module, "get_comparison_pipeline", lambda: pipeline)
    response = client.post("/api/comparisons", files={
        "baseline": ("before.jpg", b"baseline-bytes", "image/jpeg"),
        "current": ("now.jpg", b"current-bytes", "image/jpeg"),
    })
    assert response.status_code == 200
    assert pipeline.received == (b"baseline-bytes", b"current-bytes")
