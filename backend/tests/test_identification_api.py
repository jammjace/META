from fastapi.testclient import TestClient

import app as app_module
from app import app

client = TestClient(app)


def test_identification_requires_exactly_front_and_back_files():
    assert client.post("/api/identifications").status_code == 422


def test_identification_rejects_non_images():
    response = client.post("/api/identifications", files={
        "front": ("front.txt", b"front", "text/plain"),
        "back": ("back.txt", b"back", "text/plain"),
    })
    assert response.status_code == 415


def test_successful_upload_preserves_front_back_order(monkeypatch):
    class FakePipeline:
        received = None
        def process(self, front, back):
            self.received = (front, back)
            return {
                "identification_id": "c" * 32,
                "status": "complete",
                "front": {"image": {"width": 800, "height": 1000, "url": "/front"}, "view": "front", "muscles": []},
                "back": {"image": {"width": 800, "height": 1000, "url": "/back"}, "view": "back", "muscles": []},
                "warnings": [],
                "model": {"provider": "meta", "name": "muse-spark-1.3"},
            }
    pipeline = FakePipeline()
    monkeypatch.setattr(app_module, "get_identification_pipeline", lambda: pipeline)
    response = client.post("/api/identifications", files={
        "front": ("front.jpg", b"front-bytes", "image/jpeg"),
        "back": ("back.jpg", b"back-bytes", "image/jpeg"),
    })
    assert response.status_code == 200
    assert pipeline.received == (b"front-bytes", b"back-bytes")


def test_old_progress_routes_are_removed():
    assert client.post("/api/comparisons").status_code == 404
