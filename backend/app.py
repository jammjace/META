from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from adapters.meta_vision import MetaVisionAdapter, MetaVisionError
from config import ConfigurationError, Settings
from models import AnalysisResult, ComparisonResult
from services.analysis_pipeline import AnalysisPipeline
from services.comparison_pipeline import ComparisonPipeline, IncompatiblePhotosError
from services.image_preprocessor import InvalidImageError
from services.pose_detector import MediaPipePoseDetector, PoseNotFoundError
from services.usage_limiter import ApiLimitReachedError, ApiUsageLimiter

settings = Settings.from_env()
app = FastAPI(title="Upper-body muscle vision MVP")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def get_pipeline() -> AnalysisPipeline:
    return AnalysisPipeline(
        storage=settings.storage_dir,
        model=MetaVisionAdapter(settings),
        detector=MediaPipePoseDetector(),
        limiter=ApiUsageLimiter(settings.storage_dir, settings.meta_api_total_limit),
    )


def get_comparison_pipeline() -> ComparisonPipeline:
    return ComparisonPipeline(
        storage=settings.storage_dir,
        model=MetaVisionAdapter(settings),
        detector=MediaPipePoseDetector(),
        limiter=ApiUsageLimiter(settings.storage_dir, settings.meta_api_total_limit),
    )


def _analysis_dir(analysis_id: str) -> Path:
    if len(analysis_id) != 32 or any(c not in "0123456789abcdef" for c in analysis_id):
        raise HTTPException(status_code=400, detail="Invalid analysis id.")
    directory = (settings.storage_dir / "analyses" / analysis_id).resolve()
    if not directory.is_relative_to(settings.storage_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid analysis path.")
    return directory


def _comparison_dir(comparison_id: str) -> Path:
    if len(comparison_id) != 32 or any(c not in "0123456789abcdef" for c in comparison_id):
        raise HTTPException(status_code=400, detail="Invalid comparison id.")
    directory = (settings.storage_dir / "comparisons" / comparison_id).resolve()
    if not directory.is_relative_to(settings.storage_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid comparison path.")
    return directory


@app.get("/api/health")
def health() -> dict[str, object]:
    return {"status": "ok", "meta_api_enabled": settings.meta_api_enabled}


@app.post("/api/analyses", response_model=AnalysisResult)
async def create_analysis(photo: UploadFile = File(...)) -> AnalysisResult:
    if photo.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, or WebP photo.")
    try:
        return get_pipeline().process(await photo.read())
    except (InvalidImageError, PoseNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ApiLimitReachedError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except MetaVisionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/comparisons", response_model=ComparisonResult)
async def create_comparison(
    baseline: UploadFile = File(...), current: UploadFile = File(...)
) -> ComparisonResult:
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if baseline.content_type not in allowed or current.content_type not in allowed:
        raise HTTPException(status_code=415, detail="Upload two JPEG, PNG, or WebP photos.")
    try:
        return get_comparison_pipeline().process(await baseline.read(), await current.read())
    except (InvalidImageError, PoseNotFoundError, IncompatiblePhotosError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ApiLimitReachedError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except MetaVisionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/analyses/{analysis_id}", response_model=AnalysisResult)
def get_analysis(analysis_id: str) -> AnalysisResult:
    path = _analysis_dir(analysis_id) / "result.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return AnalysisResult.model_validate(json.loads(path.read_text(encoding="utf-8")))


@app.get("/api/analyses/{analysis_id}/image")
def get_analysis_image(analysis_id: str) -> FileResponse:
    path = _analysis_dir(analysis_id) / "original.jpg"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Analysis image not found.")
    return FileResponse(path, media_type="image/jpeg")


@app.get("/api/comparisons/{comparison_id}", response_model=ComparisonResult)
def get_comparison(comparison_id: str) -> ComparisonResult:
    path = _comparison_dir(comparison_id) / "result.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Comparison not found.")
    return ComparisonResult.model_validate(json.loads(path.read_text(encoding="utf-8")))


@app.get("/api/comparisons/{comparison_id}/{which}/image")
def get_comparison_image(comparison_id: str, which: str) -> FileResponse:
    if which not in {"baseline", "current"}:
        raise HTTPException(status_code=400, detail="Image must be baseline or current.")
    path = _comparison_dir(comparison_id) / f"{which}_original.jpg"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Comparison image not found.")
    return FileResponse(path, media_type="image/jpeg")

