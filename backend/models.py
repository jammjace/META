from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Point(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class PixelPoint(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class Annotation(BaseModel):
    shape: Literal["polygon"] = "polygon"
    normalized_points: list[Point] = Field(min_length=3)
    pixel_points: list[PixelPoint] = Field(min_length=3)
    label_anchor: Point
    label_position: Point


class MuscleRegion(BaseModel):
    name: str
    display_name: str
    group: Literal["trapezius", "latissimus", "rhomboids", "deltoids"]
    side: Literal["left", "right", "centre"]
    visible: bool = True
    annotation: Annotation


class ModelObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    muscle_name: str
    observation: str = Field(min_length=1, max_length=240)
    visible: bool

    @field_validator("observation")
    @classmethod
    def single_line(cls, value: str) -> str:
        return " ".join(value.split())


class ModelAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    view: Literal["back", "front", "uncertain"]
    observations: list[ModelObservation]


class MuscleResult(MuscleRegion):
    observation: str


class ImageInfo(BaseModel):
    width: int
    height: int
    url: str


class AnalysisResult(BaseModel):
    analysis_id: str
    status: Literal["complete"] = "complete"
    image: ImageInfo
    view: Literal["back", "front", "uncertain"]
    muscles: list[MuscleResult]
    warnings: list[str]
    model: dict[str, str]


class MuscleProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    muscle: str
    status: Literal["visible_progress", "no_clear_change", "inconclusive"]
    observation: str = Field(min_length=1, max_length=300)
    limitation: str | None = Field(max_length=240)


class ComparisonModelAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_view: Literal["back", "front", "uncertain"]
    current_view: Literal["back", "front", "uncertain"]
    overall_summary: str = Field(min_length=1, max_length=500)
    muscle_progress: list[MuscleProgress]
    comparison_warnings: list[str]


class ComparisonSide(BaseModel):
    image: ImageInfo
    view: Literal["back", "front", "uncertain"]
    annotations: list[MuscleRegion]


class ComparisonResult(BaseModel):
    comparison_id: str
    status: Literal["complete"] = "complete"
    baseline: ComparisonSide
    current: ComparisonSide
    overall_summary: str
    muscle_progress: list[MuscleProgress]
    comparison_warnings: list[str]
    model: dict[str, str]

