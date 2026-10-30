from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
from PIL import Image

from models import Point


class PoseNotFoundError(RuntimeError):
    pass


@dataclass(frozen=True)
class PoseDetection:
    landmarks: dict[int, Point]
    visibility: dict[int, float]

    def classify_view(self) -> str:
        """Approximate orientation from MediaPipe's anatomical left/right ordering."""
        left, right = self.landmarks[11], self.landmarks[12]
        separation = abs(left.x - right.x)
        if separation < 0.08:
            return "uncertain"
        return "back" if left.x < right.x else "front"


class MediaPipePoseDetector:
    REQUIRED = (11, 12, 23, 24)

    def detect(self, jpeg: bytes) -> PoseDetection:
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
        landmarks = {
            index: Point(x=min(max(item.x, 0), 1), y=min(max(item.y, 0), 1))
            for index, item in enumerate(result.pose_landmarks.landmark)
        }
        visibility = {
            index: float(item.visibility)
            for index, item in enumerate(result.pose_landmarks.landmark)
        }
        if any(visibility.get(index, 0) < 0.45 for index in self.REQUIRED):
            raise PoseNotFoundError(
                "Both shoulders and both hips must be visible for back-muscle annotation."
            )
        return PoseDetection(landmarks=landmarks, visibility=visibility)

