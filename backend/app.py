from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from adapters.meta_vision import MetaVisionAdapter, MetaVisionError
from config import ConfigurationError, Settings
from models import IdentificationResult
from services.identification_pipeline import IdentificationPipeline, InvalidViewPairError
from services.image_preprocessor import InvalidImageError
from services.pose_detector import MediaPipePoseDetector, PoseNotFoundError
from services.usage_limiter import ApiLimitReachedError, ApiUsageLimiter

settings = Settings.from_env()

app = FastAPI(title="Upper-body muscle identification MVP")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def get_identification_pipeline() -> IdentificationPipeline:
    return IdentificationPipeline(
        model=MetaVisionAdapter(settings),
        detector=MediaPipePoseDetector(),
        limiter=ApiUsageLimiter(settings.storage_dir, settings.meta_api_total_limit),
        debug_dir=settings.debug_artifact_dir,
    )


@app.get("/api/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "meta_api_enabled": settings.meta_api_enabled,
        "photo_storage": "none",
    }


@app.post("/api/identifications", response_model=IdentificationResult)
async def create_identification(
    front: UploadFile = File(...), back: UploadFile = File(...)
) -> IdentificationResult:
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if front.content_type not in allowed or back.content_type not in allowed:
        raise HTTPException(status_code=415, detail="Upload one front and one back JPEG, PNG, or WebP photo.")
    try:
        return get_identification_pipeline().process(await front.read(), await back.read())
    except (InvalidImageError, PoseNotFoundError, InvalidViewPairError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ApiLimitReachedError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except MetaVisionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

