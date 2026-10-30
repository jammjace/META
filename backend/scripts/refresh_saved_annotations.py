"""Refresh MediaPipe geometry for saved analyses without calling the model API."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from config import Settings  # noqa: E402
from models import AnalysisResult, MuscleResult  # noqa: E402
from services.annotation_builder import build_back_annotations  # noqa: E402
from services.pose_detector import MediaPipePoseDetector  # noqa: E402


def refresh(analysis_id: str, storage: Path) -> Path:
    directory = storage / "analyses" / analysis_id
    result_path = directory / "result.json"
    image_path = directory / "preprocessed.jpg"
    if not result_path.exists() or not image_path.exists():
        raise FileNotFoundError(f"Saved analysis is incomplete: {analysis_id}")

    raw = json.loads(result_path.read_text(encoding="utf-8"))
    previous = {item["name"]: item for item in raw["muscles"]}
    pose = MediaPipePoseDetector().detect(image_path.read_bytes())
    regions = build_back_annotations(pose, raw["image"]["width"], raw["image"]["height"])
    muscles = [
        MuscleResult(
            **region.model_dump(exclude={"visible"}),
            visible=previous[region.name]["visible"],
            observation=previous[region.name]["observation"],
        )
        for region in regions
    ]
    updated = AnalysisResult.model_validate({**raw, "muscles": muscles})

    backup = directory / "result.before-annotation-refresh.json"
    if not backup.exists():
        shutil.copy2(result_path, backup)
    annotations_path = directory / "annotations.json"
    annotations_backup = directory / "annotations.before-annotation-refresh.json"
    if annotations_path.exists() and not annotations_backup.exists():
        shutil.copy2(annotations_path, annotations_backup)

    annotations_path.write_text(
        json.dumps([region.model_dump() for region in regions], indent=2),
        encoding="utf-8",
    )
    result_path.write_text(updated.model_dump_json(indent=2), encoding="utf-8")
    return result_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("analysis_id")
    args = parser.parse_args()
    path = refresh(args.analysis_id, Settings.from_env().storage_dir)
    print(f"Refreshed annotations only: {path}")


if __name__ == "__main__":
    main()

