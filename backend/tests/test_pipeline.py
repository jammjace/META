import json

import pytest

from models import ModelAnalysis, ModelObservation, Point
from services.analysis_pipeline import AnalysisPipeline
from services.pose_detector import PoseDetection
from services.usage_limiter import ApiLimitReachedError, ApiUsageLimiter


class FakeDetector:
    def detect(self, jpeg):
        points = {
            11: Point(x=.3, y=.25), 12: Point(x=.7, y=.25),
            13: Point(x=.2, y=.5), 14: Point(x=.8, y=.5),
            23: Point(x=.38, y=.72), 24: Point(x=.62, y=.72),
        }
        return PoseDetection(points, {i: 1 for i in points})


class FakeModel:
    model_name = "meta-llama/test-vision"
    calls = 0
    def preflight(self):
        pass
    def analyze(self, image, regions):
        self.calls += 1
        result = ModelAnalysis(
            view="back",
            observations=[
                ModelObservation(muscle_name=r.name, observation=f"Visible {r.display_name} contour.", visible=True)
                for r in regions
            ],
        )
        return result, {"provider_payload": "saved"}


def test_pipeline_saves_artifacts_and_reuses_result(photo_bytes, tmp_path):
    model = FakeModel()
    pipeline = AnalysisPipeline(tmp_path, model, FakeDetector(), ApiUsageLimiter(tmp_path, 1))
    result = pipeline.process(photo_bytes)
    directory = tmp_path / "analyses" / result.analysis_id
    assert model.calls == 1
    assert {p.name for p in directory.iterdir()} == {
        "original.jpg", "preprocessed.jpg", "annotations.json", "model_response.json", "result.json"
    }
    saved = json.loads((directory / "result.json").read_text())
    assert saved["muscles"][0]["observation"]
    assert json.loads((directory / "model_response.json").read_text())["provider_payload"] == "saved"
    with pytest.raises(ApiLimitReachedError):
        pipeline.process(photo_bytes)
    assert model.calls == 1

