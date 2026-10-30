from __future__ import annotations

import json
import math
import uuid
from pathlib import Path

from adapters.vision_model import VisionModel
from models import ComparisonResult, ComparisonSide, ImageInfo
from services.annotation_builder import build_back_annotations
from services.image_preprocessor import prepare_image
from services.pose_detector import MediaPipePoseDetector, PoseDetection
from services.usage_limiter import ApiUsageLimiter


class IncompatiblePhotosError(ValueError):
    pass


def _arm_angle(pose: PoseDetection, shoulder: int, elbow: int) -> float:
    a, b = pose.landmarks[shoulder], pose.landmarks[elbow]
    return math.degrees(math.atan2(b.y - a.y, b.x - a.x))


def compatibility_notes(a: PoseDetection, b: PoseDetection) -> list[str]:
    notes: list[str] = []
    for label, shoulder, elbow in (("left", 11, 13), ("right", 12, 14)):
        if abs(_arm_angle(a, shoulder, elbow) - _arm_angle(b, shoulder, elbow)) > 18:
            notes.append(f"Major {label} arm-position difference.")
    a_width = abs(a.landmarks[12].x - a.landmarks[11].x)
    b_width = abs(b.landmarks[12].x - b.landmarks[11].x)
    if min(a_width, b_width) and max(a_width, b_width) / min(a_width, b_width) > 1.25:
        notes.append("Different subject scale or image framing.")
    return notes


def apply_local_visibility(regions, pose: PoseDetection) -> None:
    """Only hide regions whose necessary local pose anchors are occluded."""
    for region in regions:
        if region.name == "left_posterior_deltoid":
            region.visible = pose.visibility.get(11, 0) >= .45 and pose.visibility.get(13, 0) >= .35
        elif region.name == "right_posterior_deltoid":
            region.visible = pose.visibility.get(12, 0) >= .45 and pose.visibility.get(14, 0) >= .35


class ComparisonPipeline:
    def __init__(self, storage: Path, model: VisionModel, detector: MediaPipePoseDetector, limiter: ApiUsageLimiter) -> None:
        self.storage, self.model, self.detector, self.limiter = storage, model, detector, limiter

    def process(self, baseline_payload: bytes, current_payload: bytes) -> ComparisonResult:
        baseline = prepare_image(baseline_payload)
        current = prepare_image(current_payload)
        baseline_pose = self.detector.detect(baseline.inference_jpeg)
        current_pose = self.detector.detect(current.inference_jpeg)
        baseline_view = baseline_pose.classify_view()
        current_view = current_pose.classify_view()
        if baseline_view == "uncertain" or current_view == "uncertain":
            raise IncompatiblePhotosError("Both photo views must be clearly detectable.")
        if baseline_view != current_view:
            raise IncompatiblePhotosError("Baseline and current photos must show the same front or back view.")
        if baseline_view != "back":
            raise IncompatiblePhotosError("This MVP currently supports comparable back photos only.")

        baseline_regions = build_back_annotations(baseline_pose, baseline.width, baseline.height)
        current_regions = build_back_annotations(current_pose, current.width, current.height)
        apply_local_visibility(baseline_regions, baseline_pose)
        apply_local_visibility(current_regions, current_pose)
        notes = compatibility_notes(baseline_pose, current_pose)
        self.model.preflight()
        comparison_id = uuid.uuid4().hex
        directory = self.storage / "comparisons" / comparison_id
        directory.mkdir(parents=True, exist_ok=False)
        for prefix, prepared, regions in (
            ("baseline", baseline, baseline_regions), ("current", current, current_regions)
        ):
            (directory / f"{prefix}_original.jpg").write_bytes(prepared.original_jpeg)
            (directory / f"{prefix}_preprocessed.jpg").write_bytes(prepared.inference_jpeg)
            (directory / f"{prefix}_annotations.json").write_text(
                json.dumps([region.model_dump() for region in regions], indent=2), encoding="utf-8"
            )
        self.limiter.reserve()
        analysis, raw = self.model.compare(
            baseline.inference_jpeg, current.inference_jpeg, baseline_regions, notes
        )
        if analysis.baseline_view != baseline_view or analysis.current_view != current_view:
            raise IncompatiblePhotosError(
                "Model view classification did not match the local pose classification."
            )
        (directory / "model_response.json").write_text(json.dumps(raw, indent=2), encoding="utf-8")
        result = ComparisonResult(
            comparison_id=comparison_id,
            baseline=ComparisonSide(
                image=ImageInfo(width=baseline.width, height=baseline.height, url=f"/api/comparisons/{comparison_id}/baseline/image"),
                view=baseline_view, annotations=baseline_regions,
            ),
            current=ComparisonSide(
                image=ImageInfo(width=current.width, height=current.height, url=f"/api/comparisons/{comparison_id}/current/image"),
                view=current_view, annotations=current_regions,
            ),
            overall_summary=analysis.overall_summary,
            muscle_progress=analysis.muscle_progress,
            comparison_warnings=list(dict.fromkeys(notes + analysis.comparison_warnings + [
                "Visible differences may reflect pose, lighting, framing, or body composition rather than muscle growth."
            ])),
            model={"provider": "meta", "name": self.model.model_name},
        )
        (directory / "result.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return result
