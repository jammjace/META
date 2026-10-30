from __future__ import annotations

import json
import uuid
from pathlib import Path

from adapters.vision_model import VisionModel
from models import AnalysisResult, ImageInfo, MuscleResult
from services.annotation_builder import build_back_annotations
from services.image_preprocessor import prepare_image
from services.pose_detector import MediaPipePoseDetector
from services.usage_limiter import ApiUsageLimiter


class AnalysisPipeline:
    def __init__(
        self,
        storage: Path,
        model: VisionModel,
        detector: MediaPipePoseDetector,
        limiter: ApiUsageLimiter,
    ) -> None:
        self.storage = storage
        self.model = model
        self.detector = detector
        self.limiter = limiter

    def process(self, payload: bytes) -> AnalysisResult:
        prepared = prepare_image(payload)
        pose = self.detector.detect(prepared.inference_jpeg)
        regions = build_back_annotations(pose, prepared.width, prepared.height)
        self.model.preflight()
        analysis_id = uuid.uuid4().hex
        directory = self.storage / "analyses" / analysis_id
        directory.mkdir(parents=True, exist_ok=False)
        (directory / "original.jpg").write_bytes(prepared.original_jpeg)
        (directory / "preprocessed.jpg").write_bytes(prepared.inference_jpeg)
        (directory / "annotations.json").write_text(
            json.dumps([region.model_dump() for region in regions], indent=2), encoding="utf-8"
        )
        self.limiter.reserve()
        model_result, raw = self.model.analyze(prepared.inference_jpeg, regions)
        (directory / "model_response.json").write_text(
            json.dumps(raw, indent=2), encoding="utf-8"
        )
        by_name = {item.muscle_name: item for item in model_result.observations}
        muscles = [
            MuscleResult(
                **region.model_dump(exclude={"visible"}),
                visible=by_name[region.name].visible,
                observation=by_name[region.name].observation,
            )
            for region in regions
        ]
        result = AnalysisResult(
            analysis_id=analysis_id,
            image=ImageInfo(
                width=prepared.width,
                height=prepared.height,
                url=f"/api/analyses/{analysis_id}/image",
            ),
            view=model_result.view,
            muscles=muscles,
            warnings=[
                "Annotations are approximate regions derived from pose landmarks, not muscle segmentation.",
                "Visible appearance varies with pose, lighting, camera angle, and body composition.",
            ],
            model={"provider": "meta", "name": self.model.model_name},
        )
        (directory / "result.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return result

