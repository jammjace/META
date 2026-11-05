from __future__ import annotations

import json
import uuid
from pathlib import Path

from adapters.vision_model import VisionModel
from models import (
    IdentificationResult,
    IdentificationSide,
    IdentifiedMuscleResult,
    GroundingBox,
    GroundingPoint,
    ImageInfo,
    MuscleRegion,
    PixelPoint,
    Point,
)
from services.annotation_builder import build_back_annotations, build_front_annotations
from services.image_preprocessor import ImageTransform, prepare_image
from services.pose_detector import MediaPipePoseDetector, PoseDetection
from services.usage_limiter import ApiUsageLimiter


class InvalidViewPairError(ValueError):
    pass


def _required_landmarks(region: MuscleRegion) -> tuple[int, ...]:
    side = 11 if region.side == "left" else 12
    elbow = 13 if region.side == "left" else 14
    hip = 23 if region.side == "left" else 24
    if "deltoid" in region.name or "biceps" in region.name or "triceps" in region.name:
        return side, elbow
    if "pectoralis" in region.name:
        return 11, 12
    if "oblique" in region.name:
        return side, hip
    if "latissimus" in region.name:
        return side, hip, 11, 12
    return 11, 12, 23, 24


def _locally_visible(region: MuscleRegion, pose: PoseDetection) -> bool:
    threshold = .40 if region.group == "arms" else .45
    return all(
        index in pose.landmarks and pose.visibility.get(index, 0) >= threshold
        for index in _required_landmarks(region)
    )


def _source_grounding(point: GroundingPoint | None, transform: ImageTransform) -> GroundingPoint | None:
    if point is None:
        return None
    x, y = transform.inference_to_source(point.x / 1000, point.y / 1000)
    if not (0 <= x <= 1 and 0 <= y <= 1):
        return None
    return GroundingPoint(x=round(x * 1000), y=round(y * 1000))


def _source_box(box: GroundingBox | None, transform: ImageTransform) -> GroundingBox | None:
    if box is None or box.x_min >= box.x_max or box.y_min >= box.y_max:
        return None
    top_left = _source_grounding(GroundingPoint(x=box.x_min, y=box.y_min), transform)
    bottom_right = _source_grounding(GroundingPoint(x=box.x_max, y=box.y_max), transform)
    if top_left is None or bottom_right is None:
        return None
    if top_left.x >= bottom_right.x or top_left.y >= bottom_right.y:
        return None
    return GroundingBox(
        x_min=top_left.x, y_min=top_left.y,
        x_max=bottom_right.x, y_max=bottom_right.y,
    )


def _source_boundary_points(
    points: list[GroundingPoint], transform: ImageTransform,
) -> list[GroundingPoint]:
    converted = [_source_grounding(point, transform) for point in points]
    return [point for point in converted if point is not None]


def _localization_anchor(
    point: GroundingPoint | None,
    box: GroundingBox | None,
    boundary_points: list[GroundingPoint],
) -> GroundingPoint | None:
    if box is not None:
        return GroundingPoint(x=round((box.x_min + box.x_max) / 2), y=round((box.y_min + box.y_max) / 2))
    if point is not None:
        return point
    if boundary_points:
        return GroundingPoint(
            x=round(sum(item.x for item in boundary_points) / len(boundary_points)),
            y=round(sum(item.y for item in boundary_points) / len(boundary_points)),
        )
    return None


def _ground_region(
    region: MuscleRegion,
    grounding: GroundingPoint | None,
    pose: PoseDetection,
    width: int,
    height: int,
    estimated_deep: bool,
) -> MuscleRegion | None:
    if grounding is None:
        return None
    points = region.annotation.normalized_points
    centre_x = sum(point.x for point in points) / len(points)
    centre_y = sum(point.y for point in points) / len(points)
    target_x, target_y = grounding.x / 1000, grounding.y / 1000
    distance = ((target_x - centre_x) ** 2 + (target_y - centre_y) ** 2) ** .5
    if distance > .32:
        return None

    # Muse corrects placement, but MediaPipe limits how far the anatomy template moves.
    dx = max(-.08, min(.08, (target_x - centre_x) * .45))
    dy = max(-.08, min(.08, (target_y - centre_y) * .45))
    body_points = [
        point for index, point in pose.landmarks.items()
        if pose.visibility.get(index, 0) >= .25
    ]
    min_x = max(0.0, min(point.x for point in body_points) - .06)
    max_x = min(1.0, max(point.x for point in body_points) + .06)
    min_y = max(0.0, min(point.y for point in body_points) - .08)
    max_y = min(1.0, max(point.y for point in body_points) + .08)
    spine = (pose.landmarks[11].x + pose.landmarks[12].x) / 2
    original_left_of_spine = centre_x < spine

    def constrained(x: float, y: float) -> Point:
        x = max(min_x, min(max_x, x))
        y = max(min_y, min(max_y, y))
        if region.side != "centre":
            if original_left_of_spine:
                x = min(x, spine - .002)
            else:
                x = max(x, spine + .002)
        return Point(x=x, y=y)

    shifted_centre = constrained(centre_x + dx, centre_y + dy)
    if estimated_deep:
        xs, ys = [p.x for p in points], [p.y for p in points]
        rx = max(.025, min(.06, (max(xs) - min(xs)) * .28))
        ry = max(.035, min(.08, (max(ys) - min(ys)) * .28))
        adjusted = [
            constrained(shifted_centre.x + ox * rx, shifted_centre.y + oy * ry)
            for ox, oy in ((0, -1), (.7, -.7), (1, 0), (.7, .7), (0, 1), (-.7, .7), (-1, 0), (-.7, -.7))
        ]
        shape = "estimated_area"
    else:
        adjusted = [constrained(point.x + dx, point.y + dy) for point in points]
        shape = "polygon"
    pixels = [
        PixelPoint(x=min(round(point.x * width), width - 1), y=min(round(point.y * height), height - 1))
        for point in adjusted
    ]
    annotation = region.annotation.model_copy(update={
        "shape": shape,
        "normalized_points": adjusted,
        "pixel_points": pixels,
        "label_anchor": shifted_centre,
    })
    return region.model_copy(update={"annotation": annotation})


class IdentificationPipeline:
    def __init__(
        self,
        model: VisionModel,
        detector: MediaPipePoseDetector,
        limiter: ApiUsageLimiter,
        debug_dir: Path | None = None,
    ) -> None:
        self.model, self.detector, self.limiter = model, detector, limiter
        self.debug_dir = debug_dir

    def process(self, front_payload: bytes, back_payload: bytes) -> IdentificationResult:
        front = prepare_image(front_payload)
        back = prepare_image(back_payload)
        front_pose = self.detector.detect(front.inference_jpeg, front.transform)
        back_pose = self.detector.detect(back.inference_jpeg, back.transform)
        front_view, front_mirrored = front_pose.assess_view("front")
        back_view, back_mirrored = back_pose.assess_view("back")
        if front_view != "front" or back_view != "back":
            raise InvalidViewPairError(
                "Upload a clear front-facing photo first and a clear back-facing photo second."
            )
        front_regions = build_front_annotations(front_pose, front.width, front.height)
        back_regions = build_back_annotations(back_pose, back.width, back.height)
        for region in front_regions:
            region.visible = _locally_visible(region, front_pose)
        for region in back_regions:
            region.visible = _locally_visible(region, back_pose)

        self.model.preflight()
        self.limiter.reserve()
        analysis, _raw = self.model.identify_pair(
            front.inference_jpeg, back.inference_jpeg, front_regions, back_regions
        )
        if analysis.front_view != "front" or analysis.back_view != "back":
            raise InvalidViewPairError("Muse could not confirm the requested front and back views.")
        by_name = {item.muscle_name: item for item in analysis.muscles}
        warnings = list(analysis.warnings)
        if front_mirrored:
            warnings.append("The front photo appears horizontally mirrored; anatomical side labels follow MediaPipe handedness.")
        if back_mirrored:
            warnings.append("The back photo appears horizontally mirrored; anatomical side labels follow MediaPipe handedness.")

        def identified(
            regions: list[MuscleRegion], pose: PoseDetection, transform: ImageTransform,
            width: int, height: int,
        ) -> list[IdentifiedMuscleResult]:
            output = []
            for region in regions:
                item = by_name[region.name]
                if not region.visible or item.location_quality == "not_meaningfully_locatable":
                    continue
                source_grounding = _source_grounding(item.grounding_point, transform)
                source_box = _source_box(item.grounding_box, transform)
                source_boundary = _source_boundary_points(item.boundary_points, transform)
                localization_anchor = _localization_anchor(source_grounding, source_box, source_boundary)
                anatomically_deep = "rhomboid" in region.name or region.name == "erector_spinae"
                if anatomically_deep:
                    effective_quality = "estimated_deep"
                elif item.location_quality in {"covered_surface", "estimated_deep"}:
                    # Non-deep candidates such as pectorals remain surface-shaped
                    # estimates even when clothing obscures their visual boundary.
                    effective_quality = "covered_surface"
                else:
                    effective_quality = "visible_surface"
                grounded = _ground_region(
                    region, localization_anchor, pose, width, height,
                    anatomically_deep,
                )
                if grounded is None:
                    warnings.append(f"Skipped {region.display_name}: grounding point did not agree with pose geometry or image bounds.")
                    continue
                output.append(IdentifiedMuscleResult(
                    **grounded.model_dump(),
                    location_quality=effective_quality,
                    observation=item.observation,
                    template_annotation=region.annotation,
                    grounding_point=source_grounding,
                    grounding_box=source_box,
                    boundary_points=source_boundary,
                ))
            return output

        identification_id = uuid.uuid4().hex
        result = IdentificationResult(
            identification_id=identification_id,
            front=IdentificationSide(
                image=ImageInfo(width=front.width, height=front.height, url=""),
                view="front", muscles=identified(front_regions, front_pose, front.transform, front.width, front.height),
            ),
            back=IdentificationSide(
                image=ImageInfo(width=back.width, height=back.height, url=""),
                view="back", muscles=identified(back_regions, back_pose, back.transform, back.width, back.height),
            ),
            warnings=list(dict.fromkeys(warnings + [
                "Colored regions are pose-anchored anatomical approximations, not segmented muscle boundaries.",
                "Deeper muscles are labeled as estimated anatomical locations."
            ])),
            model={"provider": "meta", "name": self.model.model_name},
        )
        if self.debug_dir is not None:
            self.debug_dir.mkdir(parents=True, exist_ok=True)
            debug = {
                "identification_id": identification_id,
                "contains_photo_bytes": False,
                "front": self._debug_side(front, front_pose, front_regions, front_mirrored),
                "back": self._debug_side(back, back_pose, back_regions, back_mirrored),
                "model_result": analysis.model_dump(mode="json"),
                "final_result": result.model_dump(mode="json"),
            }
            (self.debug_dir / f"{identification_id}.json").write_text(
                json.dumps(debug, indent=2), encoding="utf-8"
            )
        return result

    @staticmethod
    def _debug_side(prepared, pose, regions, mirrored: bool) -> dict:
        return {
            "source_size": [prepared.width, prepared.height],
            "transform": prepared.transform.__dict__,
            "mirrored": mirrored,
            "face_visibility": pose.face_visibility,
            "landmarks": {
                str(index): {"x": point.x, "y": point.y, "visibility": pose.visibility.get(index, 0)}
                for index, point in pose.landmarks.items()
            },
            "candidate_regions": [region.model_dump(mode="json") for region in regions],
        }
