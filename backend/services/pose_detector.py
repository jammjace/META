from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
from PIL import Image

from models import Point
from services.image_preprocessor import ImageTransform


class PoseNotFoundError(RuntimeError):
    pass


def _map_pose_landmarks(items, transform: ImageTransform | None):
    landmarks: dict[int, Point] = {}
    visibility: dict[int, float] = {}
    depth: dict[int, float] = {}
    invalid: set[int] = set()
    for index, item in enumerate(items):
        visibility[index] = float(item.visibility)
        depth[index] = float(item.z)
        x, y = item.x, item.y
        if transform is not None:
            x, y = transform.inference_to_source(x, y)
        if 0 <= x <= 1 and 0 <= y <= 1:
            landmarks[index] = Point(x=x, y=y)
        else:
            invalid.add(index)
    return landmarks, visibility, depth, invalid


@dataclass(frozen=True)
class PoseDetection:
    landmarks: dict[int, Point]
    visibility: dict[int, float]
    depth: dict[int, float] | None = None

    def classify_view(self) -> str:
        """Legacy shoulder-order heuristic, retained only for diagnostics."""
        left, right = self.landmarks[11], self.landmarks[12]
        separation = abs(left.x - right.x)
        if separation < 0.08:
            return "uncertain"
        return "back" if left.x < right.x else "front"

    @property
    def face_visibility(self) -> float:
        values = [
            self.visibility[index]
            for index in (0, 2, 5, 7, 8, 9, 10)
            if index in self.visibility and index in self.landmarks
        ]
        return sum(values) / len(values) if values else 0.0

    def assess_view(self, expected: str) -> tuple[str, bool]:
        """Use the explicit upload slot as view and report horizontal mirroring.

        MediaPipe cannot reliably distinguish a back from a mirrored front pose:
        its face visibility may also remain high on back photos. Semantic view
        confirmation is therefore delegated to Muse's existing one-call result.
        """
        left, right = self.landmarks[11], self.landmarks[12]
        normal_order = left.x > right.x if expected == "front" else left.x < right.x
        return expected, not normal_order


class MediaPipePoseDetector:
    REQUIRED = (11, 12, 23, 24)

    def detect(self, jpeg: bytes, transform: ImageTransform | None = None) -> PoseDetection:
        try:
            import mediapipe as mp
        except ImportError as exc:
            raise RuntimeError("MediaPipe is not installed.") from exc
        image = np.asarray(Image.open(io.BytesIO(jpeg)).convert("RGB"))
        with mp.solutions.pose.Pose(
            static_image_mode=True,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5,
        ) as pose:
            result = pose.process(image)
        if not result.pose_landmarks:
            raise PoseNotFoundError("No upper-body pose was detected in the photo.")
        landmarks, visibility, depth, invalid = _map_pose_landmarks(
            result.pose_landmarks.landmark, transform
        )
        off_frame_required = invalid.intersection(self.REQUIRED)
        if off_frame_required:
            names = {11: "left shoulder", 12: "right shoulder", 23: "left hip", 24: "right hip"}
            missing = ", ".join(names[index] for index in sorted(off_frame_required))
            raise PoseNotFoundError(f"Required pose landmarks are outside the photo: {missing}.")
        if any(visibility.get(index, 0) < 0.45 for index in self.REQUIRED):
            raise PoseNotFoundError(
                "Both shoulders and both hips must be visible for back-muscle annotation."
            )
        return PoseDetection(landmarks=landmarks, visibility=visibility, depth=depth)

