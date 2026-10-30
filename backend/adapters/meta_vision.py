from __future__ import annotations

import base64
import json

from config import Settings
from models import ComparisonModelAnalysis, ModelAnalysis, MuscleRegion


class MetaVisionError(RuntimeError):
    pass


class MetaVisionAdapter:
    """One image and all regions in exactly one non-retried model request."""

    def __init__(self, settings: Settings, client: object | None = None) -> None:
        self.settings = settings
        self.model_name = settings.model_api_model
        if client is None:
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.model_api_key,
                base_url=settings.model_api_base_url,
                timeout=settings.meta_api_timeout_seconds,
                max_retries=0,
            )
        self._client = client

    def preflight(self) -> None:
        self.settings.validate_meta()

    def analyze(
        self, image_jpeg: bytes, regions: list[MuscleRegion]
    ) -> tuple[ModelAnalysis, dict]:
        self.preflight()
        names = [region.name for region in regions]
        prompt = (
            "Analyze this single upper-body BACK photo for visible muscle development. "
            "Return one short, neutral visual observation for every supplied muscle name. "
            "Discuss only visible contour, symmetry, separation, or definition; do not diagnose, "
            "score, recommend exercises, or claim measured muscle mass. Mark visible=false when "
            "a region is obscured. The allowed muscle names are: "
            + ", ".join(names)
            + '. Return JSON exactly as {"view":"back|front|uncertain","observations":'
              '[{"muscle_name":"...","observation":"...","visible":true}]}. '
              "Include every allowed name exactly once and no other names."
        )
        image = base64.b64encode(image_jpeg).decode("ascii")
        try:
            response = self._client.responses.create(
                model=self.model_name,
                input=[{
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{image}",
                        },
                    ],
                }],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "muscle_analysis",
                        "schema": ModelAnalysis.model_json_schema(),
                        "strict": True,
                    }
                },
            )
            parsed = ModelAnalysis.model_validate(json.loads(response.output_text))
            raw = response.model_dump(mode="json")
        except Exception as exc:
            raise MetaVisionError("The Meta vision request failed; it was not retried.") from exc
        returned = [item.muscle_name for item in parsed.observations]
        if len(returned) != len(names) or set(returned) != set(names):
            raise MetaVisionError("Meta returned an incomplete or unexpected muscle list.")
        return parsed, raw

    def compare(
        self,
        baseline_jpeg: bytes,
        current_jpeg: bytes,
        regions: list[MuscleRegion],
        compatibility_notes: list[str],
    ) -> tuple[ComparisonModelAnalysis, dict]:
        """Compare two ordered images in exactly one non-retried Responses call."""
        self.preflight()
        names = [region.name for region in regions]
        notes = "; ".join(compatibility_notes) if compatibility_notes else "No major local pose differences detected."
        prompt = (
            "Compare two upper-body progress photos. The FIRST image is the BASELINE and the "
            "SECOND image is the CURRENT photo. Analyze only visible differences in contour, "
            "fullness, width, and definition for these exact regions: " + ", ".join(names) + ". "
            "For every region return status visible_progress, no_clear_change, or inconclusive. "
            "Use inconclusive whenever pose, framing, lighting, occlusion, or visibility prevents "
            "a reliable visual comparison. Do not infer muscle mass, strength, training effect, "
            "or precise measurements. Local MediaPipe compatibility notes: " + notes
        )
        baseline = base64.b64encode(baseline_jpeg).decode("ascii")
        current = base64.b64encode(current_jpeg).decode("ascii")
        try:
            response = self._client.responses.create(
                model=self.model_name,
                input=[{
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": f"data:image/jpeg;base64,{baseline}"},
                        {"type": "input_image", "image_url": f"data:image/jpeg;base64,{current}"},
                    ],
                }],
                text={"format": {
                    "type": "json_schema",
                    "name": "muscle_progress_comparison",
                    "schema": ComparisonModelAnalysis.model_json_schema(),
                    "strict": True,
                }},
            )
            parsed = ComparisonModelAnalysis.model_validate(json.loads(response.output_text))
            raw = response.model_dump(mode="json")
        except Exception as exc:
            raise MetaVisionError("The Meta comparison request failed; it was not retried.") from exc
        returned = [item.muscle for item in parsed.muscle_progress]
        if len(returned) != len(names) or set(returned) != set(names):
            raise MetaVisionError("Meta returned an incomplete or unexpected comparison muscle list.")
        return parsed, raw

