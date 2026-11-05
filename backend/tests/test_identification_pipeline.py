import io

import pytest
from PIL import Image

from models import GroundingBox, GroundingPoint, IdentificationModelResult, IdentifiedMuscle, Point
from services.identification_pipeline import IdentificationPipeline, InvalidViewPairError
from services.identification_pipeline import _source_boundary_points, _source_box
from services.image_preprocessor import ImageTransform
from services.pose_detector import PoseDetection
from services.usage_limiter import ApiLimitReachedError, ApiUsageLimiter


def photo(width=800, height=1000, color=(90, 90, 90)):
    output = io.BytesIO()
    Image.new("RGB", (width, height), color).save(output, "JPEG")
    return output.getvalue()


def pose(view):
    left_x, right_x = ((.7, .3) if view == "front" else (.3, .7))
    points = {
        11: Point(x=left_x, y=.25), 12: Point(x=right_x, y=.25),
        13: Point(x=min(1, left_x + (.1 if left_x > .5 else -.1)), y=.5),
        14: Point(x=min(1, right_x + (.1 if right_x > .5 else -.1)), y=.5),
        23: Point(x=.62 if left_x > .5 else .38, y=.72),
        24: Point(x=.38 if right_x < .5 else .62, y=.72),
    }
    points.update({index: Point(x=.5, y=.1) for index in (0, 2, 5, 7, 8, 9, 10)})
    visibility = {index: 1 for index in points}
    visibility.update({index: (1 if view == "front" else .05) for index in (0, 2, 5, 7, 8, 9, 10)})
    return PoseDetection(points, visibility)


class SequenceDetector:
    def __init__(self, *items): self.items = iter(items)
    def detect(self, image, transform=None): return next(self.items)


class FakeIdentificationModel:
    model_name = "muse-spark-1.3"
    calls = 0
    def preflight(self): pass
    def identify_pair(self, front, back, front_regions, back_regions):
        self.calls += 1
        items = []
        for view, regions in (("front", front_regions), ("back", back_regions)):
            for region in regions:
                points = region.annotation.normalized_points
                x = round(sum(point.x for point in points) / len(points) * 1000)
                y = round(sum(point.y for point in points) / len(points) * 1000)
                items.append(IdentifiedMuscle(
                    muscle_name=region.name,
                    view=view,
                    location_quality="estimated_deep" if "rhomboid" in region.name else "visible_surface",
                    observation=f"Approximate {region.display_name} location.",
                    grounding_point=GroundingPoint(x=x, y=y),
                    grounding_box=GroundingBox(
                        x_min=max(0, x - 40), y_min=max(0, y - 50),
                        x_max=min(1000, x + 40), y_max=min(1000, y + 50),
                    ),
                    boundary_points=[],
                ))
        return IdentificationModelResult(
            front_view="front", back_view="back", muscles=items, warnings=[]
        ), {"id": "mock"}


def test_front_back_identification_uses_one_call_and_memory_only(tmp_path):
    model = FakeIdentificationModel()
    pipeline = IdentificationPipeline(
        model, SequenceDetector(pose("front"), pose("back")),
        ApiUsageLimiter(tmp_path, 1),
    )
    result = pipeline.process(photo(800, 1000), photo(700, 900, (100, 100, 100)))
    assert model.calls == 1
    assert result.front.view == "front" and result.back.view == "back"
    assert {muscle.group for muscle in result.front.muscles} == {"chest", "shoulders", "arms", "core", "obliques"}
    assert any(muscle.location_quality == "estimated_deep" for muscle in result.back.muscles)
    assert not (tmp_path / "identifications").exists()
    with pytest.raises(ApiLimitReachedError):
        IdentificationPipeline(
            model, SequenceDetector(pose("front"), pose("back")),
            ApiUsageLimiter(tmp_path, 1),
        ).process(photo(), photo())
    assert model.calls == 1


def test_semantic_view_mismatch_is_rejected_after_single_model_confirmation(tmp_path):
    class WrongViewModel(FakeIdentificationModel):
        def identify_pair(self, *args):
            result, raw = super().identify_pair(*args)
            result.front_view = "back"
            result.back_view = "front"
            return result, raw
    model = WrongViewModel()
    pipeline = IdentificationPipeline(
        model, SequenceDetector(pose("back"), pose("front")),
        ApiUsageLimiter(tmp_path, 1),
    )
    with pytest.raises(InvalidViewPairError):
        pipeline.process(photo(), photo())
    assert model.calls == 1
    assert (tmp_path / "api_usage.json").exists()


def test_grounding_disagreement_skips_region(tmp_path):
    class BadGroundingModel(FakeIdentificationModel):
        def identify_pair(self, *args):
            result, raw = super().identify_pair(*args)
            target = next(item for item in result.muscles if item.muscle_name == "rectus_abdominis")
            target.grounding_point = GroundingPoint(x=0, y=0)
            target.grounding_box = None
            return result, raw
    result = IdentificationPipeline(
        BadGroundingModel(), SequenceDetector(pose("front"), pose("back")),
        ApiUsageLimiter(tmp_path, 1),
    ).process(photo(), photo())
    assert all(muscle.name != "rectus_abdominis" for muscle in result.front.muscles)
    assert any("grounding point" in warning for warning in result.warnings)


def test_occluded_arm_region_is_skipped(tmp_path):
    front_pose = pose("front")
    front_pose.visibility[13] = 0
    result = IdentificationPipeline(
        FakeIdentificationModel(), SequenceDetector(front_pose, pose("back")),
        ApiUsageLimiter(tmp_path, 1),
    ).process(photo(), photo())
    assert all(muscle.name != "left_biceps_brachii" for muscle in result.front.muscles)


def test_mirrored_pair_is_accepted_and_reported_without_using_shoulder_order_as_view(tmp_path):
    front = pose("front")
    back = pose("back")
    front.landmarks[11], front.landmarks[12] = front.landmarks[12], front.landmarks[11]
    back.landmarks[11], back.landmarks[12] = back.landmarks[12], back.landmarks[11]
    result = IdentificationPipeline(
        FakeIdentificationModel(), SequenceDetector(front, back), ApiUsageLimiter(tmp_path, 1)
    ).process(photo(), photo())
    assert sum("mirrored" in warning for warning in result.warnings) == 2
    left = next(muscle for muscle in result.front.muscles if muscle.name == "left_pectoralis_major")
    right = next(muscle for muscle in result.front.muscles if muscle.name == "right_pectoralis_major")
    assert left.side == "left" and right.side == "right"
    assert left.grounding_point.x < right.grounding_point.x


def test_box_and_boundary_coordinates_map_out_of_letterbox_space():
    transform = ImageTransform(
        source_width=800, source_height=1000,
        inference_width=1000, inference_height=1000,
        scaled_width=800, scaled_height=1000, offset_x=100, offset_y=0,
    )
    box = _source_box(GroundingBox(x_min=200, y_min=250, x_max=800, y_max=750), transform)
    assert box == GroundingBox(x_min=125, y_min=250, x_max=875, y_max=750)
    points = _source_boundary_points(
        [GroundingPoint(x=200, y=250), GroundingPoint(x=800, y=750)], transform
    )
    assert points == [GroundingPoint(x=125, y=250), GroundingPoint(x=875, y=750)]
    assert _source_box(GroundingBox(x_min=0, y_min=100, x_max=80, y_max=200), transform) is None


def test_debug_artifact_is_json_only_and_contains_transforms_not_photos(tmp_path):
    debug_dir = tmp_path / "debug"
    result = IdentificationPipeline(
        FakeIdentificationModel(), SequenceDetector(pose("front"), pose("back")),
        ApiUsageLimiter(tmp_path, 1), debug_dir=debug_dir,
    ).process(photo(), photo())
    files = list(debug_dir.iterdir())
    assert [file.suffix for file in files] == [".json"]
    data = files[0].read_text(encoding="utf-8")
    assert result.identification_id in data
    assert '"contains_photo_bytes": false' in data
    assert "original_jpeg" not in data and "inference_jpeg" not in data


def test_low_visibility_hip_removes_only_dependent_core_and_back_regions(tmp_path):
    front = pose("front")
    front.visibility[23] = .2
    result = IdentificationPipeline(
        FakeIdentificationModel(), SequenceDetector(front, pose("back")),
        ApiUsageLimiter(tmp_path, 1),
    ).process(photo(), photo())
    names = {muscle.name for muscle in result.front.muscles}
    assert "left_external_oblique" not in names
    assert "left_pectoralis_major" in names


def test_deep_back_muscles_remain_estimated_even_if_mock_model_calls_them_surface(tmp_path):
    class OverconfidentModel(FakeIdentificationModel):
        def identify_pair(self, *args):
            result, raw = super().identify_pair(*args)
            for item in result.muscles:
                if "rhomboid" in item.muscle_name or item.muscle_name == "erector_spinae":
                    item.location_quality = "visible_surface"
            return result, raw
    result = IdentificationPipeline(
        OverconfidentModel(), SequenceDetector(pose("front"), pose("back")),
        ApiUsageLimiter(tmp_path, 1),
    ).process(photo(), photo())
    deep = [
        muscle for muscle in result.back.muscles
        if "rhomboid" in muscle.name or muscle.name == "erector_spinae"
    ]
    assert {muscle.name for muscle in deep} == {"left_rhomboid", "right_rhomboid", "erector_spinae"}
    assert all(muscle.location_quality == "estimated_deep" for muscle in deep)
    assert all(muscle.annotation.shape == "estimated_area" for muscle in deep)


def test_covered_surface_muscle_keeps_template_shape_instead_of_deep_oval(tmp_path):
    class CoveredChestModel(FakeIdentificationModel):
        def identify_pair(self, *args):
            result, raw = super().identify_pair(*args)
            target = next(item for item in result.muscles if item.muscle_name == "left_pectoralis_major")
            target.location_quality = "covered_surface"
            return result, raw
    result = IdentificationPipeline(
        CoveredChestModel(), SequenceDetector(pose("front"), pose("back")),
        ApiUsageLimiter(tmp_path, 1),
    ).process(photo(), photo())
    chest = next(muscle for muscle in result.front.muscles if muscle.name == "left_pectoralis_major")
    assert chest.location_quality == "covered_surface"
    assert chest.annotation.shape == "polygon"
    assert len(chest.annotation.normalized_points) == len(chest.template_annotation.normalized_points)
