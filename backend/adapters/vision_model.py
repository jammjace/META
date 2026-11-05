from __future__ import annotations

from typing import Protocol

from models import IdentificationModelResult, MuscleRegion


class VisionModel(Protocol):
    model_name: str

    def preflight(self) -> None: ...

    def identify_pair(
        self,
        front_jpeg: bytes,
        back_jpeg: bytes,
        front_regions: list[MuscleRegion],
        back_regions: list[MuscleRegion],
    ) -> tuple[IdentificationModelResult, dict]: ...

