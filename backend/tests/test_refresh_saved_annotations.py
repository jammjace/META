import json

from models import Point
from scripts import refresh_saved_annotations as migration
from services.pose_detector import PoseDetection


class FakeDetector:
    def detect(self, image):
        points = {
            11: Point(x=.3, y=.25), 12: Point(x=.7, y=.25),
            13: Point(x=.2, y=.5), 14: Point(x=.8, y=.5),
            23: Point(x=.38, y=.72), 24: Point(x=.62, y=.72),
        }
        return PoseDetection(points, {index: 1 for index in points})


def test_refresh_preserves_observations_and_raw_model_response(tmp_path, monkeypatch):
    analysis_id = "a" * 32
    directory = tmp_path / "analyses" / analysis_id
    directory.mkdir(parents=True)
    (directory / "preprocessed.jpg").write_bytes(b"saved image")
    raw_model = '{"id":"paid-response-is-untouched"}'
    (directory / "model_response.json").write_text(raw_model, encoding="utf-8")
    names = [
        "trapezius", "left_rhomboid", "right_rhomboid",
        "left_latissimus_dorsi", "right_latissimus_dorsi",
        "left_posterior_deltoid", "right_posterior_deltoid",
    ]
    old_result = {
        "analysis_id": analysis_id,
        "status": "complete",
        "image": {"width": 800, "height": 1000, "url": f"/api/analyses/{analysis_id}/image"},
        "view": "back",
        "muscles": [
            {"name": name, "visible": True, "observation": f"Saved observation for {name}."}
            for name in names
        ],
        "warnings": ["approximate"],
        "model": {"provider": "meta", "name": "muse-spark-1.3"},
    }
    (directory / "result.json").write_text(json.dumps(old_result), encoding="utf-8")
    (directory / "annotations.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(migration, "MediaPipePoseDetector", FakeDetector)

    migration.refresh(analysis_id, tmp_path)

    updated = json.loads((directory / "result.json").read_text(encoding="utf-8"))
    assert updated["muscles"][0]["observation"] == "Saved observation for trapezius."
    assert updated["muscles"][0]["group"] == "trapezius"
    assert updated["muscles"][0]["annotation"]["label_position"]
    assert (directory / "model_response.json").read_text(encoding="utf-8") == raw_model
    assert (directory / "result.before-annotation-refresh.json").exists()
