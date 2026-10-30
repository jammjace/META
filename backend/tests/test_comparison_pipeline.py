import io
import json

import pytest
from PIL import Image

from models import ComparisonModelAnalysis, MuscleProgress, Point
from services.comparison_pipeline import ComparisonPipeline, IncompatiblePhotosError
from services.pose_detector import PoseDetection
from services.usage_limiter import ApiLimitReachedError, ApiUsageLimiter


def image_bytes(width=800, height=1000):
    output = io.BytesIO()
    Image.new("RGB", (width, height), (80, 85, 90)).save(output, "JPEG")
    return output.getvalue()


def pose(view="back", arm_shift=0):
    left_x, right_x = ((.3, .7) if view == "back" else (.7, .3))
    points = {
        11: Point(x=left_x, y=.25), 12: Point(x=right_x, y=.25),
        13: Point(x=max(0, left_x - .1 + arm_shift), y=.5),
        14: Point(x=min(1, right_x + .1), y=.5),
        23: Point(x=.38 if view == "back" else .62, y=.72),
        24: Point(x=.62 if view == "back" else .38, y=.72),
    }
    return PoseDetection(points, {index: 1 for index in points})


class SequenceDetector:
    def __init__(self, *poses): self.poses = iter(poses)
    def detect(self, image): return next(self.poses)


class FakeComparisonModel:
    model_name = "muse-spark-1.3"
    calls = 0
    received = None
    def preflight(self): pass
    def compare(self, baseline, current, regions, notes):
        self.calls += 1
        self.received = (baseline, current, notes)
        return ComparisonModelAnalysis(
            baseline_view="back", current_view="back",
            overall_summary="The current photo shows a modest visible contour difference.",
            muscle_progress=[
                MuscleProgress(
                    muscle=region.name,
                    status="no_clear_change",
                    observation=f"No clear visible change for {region.display_name}.",
                    limitation=None,
                ) for region in regions
            ],
            comparison_warnings=[],
        ), {"id": "mock-comparison"}


def test_two_different_size_photos_use_one_call_and_save_ordered_artifacts(tmp_path):
    model = FakeComparisonModel()
    pipeline = ComparisonPipeline(
        tmp_path, model, SequenceDetector(pose(), pose()), ApiUsageLimiter(tmp_path, 1)
    )
    result = pipeline.process(image_bytes(800, 1000), image_bytes(600, 900))
    directory = tmp_path / "comparisons" / result.comparison_id
    assert model.calls == 1
    assert result.baseline.image.width == 800
    assert result.current.image.width == 600
    assert model.received[0] != model.received[1]
    assert (directory / "baseline_original.jpg").exists()
    assert (directory / "current_original.jpg").exists()
    assert json.loads((directory / "model_response.json").read_text())["id"] == "mock-comparison"
    with pytest.raises(ApiLimitReachedError):
        ComparisonPipeline(
            tmp_path, model, SequenceDetector(pose(), pose()), ApiUsageLimiter(tmp_path, 1)
        ).process(image_bytes(), image_bytes())
    assert model.calls == 1


def test_front_back_mismatch_is_rejected_without_model_call(tmp_path):
    model = FakeComparisonModel()
    pipeline = ComparisonPipeline(
        tmp_path, model, SequenceDetector(pose("back"), pose("front")), ApiUsageLimiter(tmp_path, 1)
    )
    with pytest.raises(IncompatiblePhotosError, match="same front or back"):
        pipeline.process(image_bytes(), image_bytes())
    assert model.calls == 0
    assert not (tmp_path / "api_usage.json").exists()


def test_invalid_second_image_fails_before_pose_or_model(tmp_path):
    model = FakeComparisonModel()
    pipeline = ComparisonPipeline(
        tmp_path, model, SequenceDetector(pose(), pose()), ApiUsageLimiter(tmp_path, 1)
    )
    with pytest.raises(ValueError):
        pipeline.process(image_bytes(), b"not an image")
    assert model.calls == 0


def test_pose_difference_is_forwarded_as_limitation_note(tmp_path):
    model = FakeComparisonModel()
    pipeline = ComparisonPipeline(
        tmp_path, model, SequenceDetector(pose(), pose(arm_shift=.25)), ApiUsageLimiter(tmp_path, 1)
    )
    result = pipeline.process(image_bytes(), image_bytes())
    assert any("arm-position" in note for note in model.received[2])
    assert any("arm-position" in warning for warning in result.comparison_warnings)


def test_occluded_elbow_hides_corresponding_deltoid_annotation(tmp_path):
    baseline_pose = pose()
    baseline_pose.visibility[13] = 0
    model = FakeComparisonModel()
    result = ComparisonPipeline(
        tmp_path, model, SequenceDetector(baseline_pose, pose()), ApiUsageLimiter(tmp_path, 1)
    ).process(image_bytes(), image_bytes())
    left = next(region for region in result.baseline.annotations if region.name == "left_posterior_deltoid")
    right = next(region for region in result.baseline.annotations if region.name == "right_posterior_deltoid")
    assert left.visible is False
    assert right.visible is True
