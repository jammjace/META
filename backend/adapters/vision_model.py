from __future__ import annotations

from typing import Protocol

from models import ComparisonModelAnalysis, ModelAnalysis, MuscleRegion


class VisionModel(Protocol):
    model_name: str

    def preflight(self) -> None: ...

    def analyze(self, image_jpeg: bytes, regions: list[MuscleRegion]) -> tuple[ModelAnalysis, dict]: ...

    def compare(
        self,
        baseline_jpeg: bytes,
        current_jpeg: bytes,
        regions: list[MuscleRegion],
        compatibility_notes: list[str],
    ) -> tuple[ComparisonModelAnalysis, dict]: ...

