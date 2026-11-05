from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Point(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class PixelPoint(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class Annotation(BaseModel):
    shape: Literal["polygon", "estimated_area"] = "polygon"
    normalized_points: list[Point] = Field(min_length=3)
    pixel_points: list[PixelPoint] = Field(min_length=3)
    label_anchor: Point
    label_position: Point


class MuscleRegion(BaseModel):
    name: str
    display_name: str
    group: Literal["chest", "shoulders", "arms", "back", "core", "obliques", "spine"]
    side: Literal["left", "right", "centre"]
    visible: bool = True
    annotation: Annotation


class ImageInfo(BaseModel):
    width: int
    height: int
    url: str


class GroundingPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: int = Field(ge=0, le=1000)
    y: int = Field(ge=0, le=1000)


class GroundingBox(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x_min: int = Field(ge=0, le=1000)
    y_min: int = Field(ge=0, le=1000)
    x_max: int = Field(ge=0, le=1000)
    y_max: int = Field(ge=0, le=1000)


class IdentifiedMuscle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    muscle_name: str
    view: Literal["front", "back"]
    location_quality: Literal[
        "visible_surface", "covered_surface", "estimated_deep", "not_meaningfully_locatable"
    ]
    observation: str = Field(min_length=1, max_length=300)
    grounding_point: GroundingPoint | None
    grounding_box: GroundingBox | None
    boundary_points: list[GroundingPoint] = Field(max_length=8)


class IdentificationModelResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    front_view: Literal["front", "back", "uncertain"]
    back_view: Literal["front", "back", "uncertain"]
    muscles: list[IdentifiedMuscle]
    warnings: list[str]


class IdentifiedMuscleResult(MuscleRegion):
    location_quality: Literal["visible_surface", "covered_surface", "estimated_deep"]
    observation: str
    template_annotation: Annotation
    grounding_point: GroundingPoint | None
    grounding_box: GroundingBox | None
    boundary_points: list[GroundingPoint]


class IdentificationSide(BaseModel):
    image: ImageInfo
    view: Literal["front", "back"]
    muscles: list[IdentifiedMuscleResult]


class IdentificationResult(BaseModel):
    identification_id: str
    status: Literal["complete"] = "complete"
    front: IdentificationSide
    back: IdentificationSide
    warnings: list[str]
    model: dict[str, str]

