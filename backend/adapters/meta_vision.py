from __future__ import annotations

import base64
import json

from config import Settings
from models import IdentificationModelResult, MuscleRegion


class MetaVisionError(RuntimeError):
    pass


class MetaVisionAdapter:
    """One front/back identification request using Meta's Responses API."""

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

    def identify_pair(
        self,
        front_jpeg: bytes,
        back_jpeg: bytes,
        front_regions: list[MuscleRegion],
        back_regions: list[MuscleRegion],
    ) -> tuple[IdentificationModelResult, dict]:
        self.preflight()
        front_names = [region.name for region in front_regions]
        back_names = [region.name for region in back_regions]
        prompt = (
            "Identify upper-body muscle anatomy in two ordered photos. The FIRST image is the "
            "FRONT view and the SECOND image is the BACK view. For each candidate muscle, describe "
            "only what the image supports. Classify location_quality as visible_surface when the "
            "surface muscle is meaningfully visible, covered_surface when a surface muscle is hidden by "
            "clothing but its broad anatomical region remains locatable, estimated_deep only when the "
            "muscle itself is anatomically deeper, or not_meaningfully_locatable "
            "when pose, clothing, crop, or image quality prevents a useful location. Anatomical left "
            "and right always mean the SUBJECT'S left and right, never the viewer's. For each meaningfully "
            "locatable surface muscle return: (1) grounding_box with x_min, y_min, x_max, y_max enclosing "
            "its approximate visible extent on Meta's normalized 0-1000 grid; (2) grounding_point near its "
            "visual centre as a fallback; and (3) boundary_points with 4 to 8 clockwise points sampling only "
            "a visually supported perimeter. Boundary points are an experimental hint, not segmentation. "
            "When a perimeter is not visually supported return an empty boundary_points list. For deeper or "
            "covered anatomy return grounding_box null, boundary_points empty, and only a grounding_point "
            "when an approximate location is meaningful. For not_meaningfully_locatable return all grounding "
            "fields empty or null. Images may contain letterbox padding; place coordinates only on the "
            "photographed body, never on the padding. For deeper muscles such as rhomboids, use estimated_deep and point to the "
            "approximate anatomical location rather than claiming a visible surface outline. "
            "Do not infer development, progress, strength, or training effects. FRONT candidates: "
            + ", ".join(front_names) + ". BACK candidates: " + ", ".join(back_names)
            + ". Include every candidate exactly once."
        )
        front = base64.b64encode(front_jpeg).decode("ascii")
        back = base64.b64encode(back_jpeg).decode("ascii")
        try:
            response = self._client.responses.create(
                model=self.model_name,
                input=[{
                    "type": "message", "role": "user", "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": f"data:image/jpeg;base64,{front}"},
                        {"type": "input_image", "image_url": f"data:image/jpeg;base64,{back}"},
                    ],
                }],
                text={"format": {
                    "type": "json_schema",
                    "name": "upper_body_muscle_identification",
                    "schema": IdentificationModelResult.model_json_schema(),
                    "strict": True,
                }},
            )
            parsed = IdentificationModelResult.model_validate(json.loads(response.output_text))
            raw = response.model_dump(mode="json")
        except Exception as exc:
            raise MetaVisionError("The Meta identification request failed; it was not retried.") from exc
        expected = set(front_names + back_names)
        returned = [item.muscle_name for item in parsed.muscles]
        if len(returned) != len(expected) or set(returned) != expected:
            raise MetaVisionError("Meta returned an incomplete or unexpected muscle list.")
        expected_view = {**{name: "front" for name in front_names}, **{name: "back" for name in back_names}}
        if any(item.view != expected_view[item.muscle_name] for item in parsed.muscles):
            raise MetaVisionError("Meta associated a muscle with the wrong photo view.")
        return parsed, raw
