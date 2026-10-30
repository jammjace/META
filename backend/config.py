from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


class ConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    storage_dir: Path
    cors_origins: tuple[str, ...]
    meta_api_enabled: bool
    model_api_key: str
    model_api_base_url: str
    model_api_model: str
    meta_api_timeout_seconds: float
    meta_api_total_limit: int

    @classmethod
    def from_env(cls) -> "Settings":
        root = Path(__file__).resolve().parent
        storage = Path(os.getenv("STORAGE_DIR", root / "storage")).resolve()
        return cls(
            storage_dir=storage,
            cors_origins=tuple(
                origin.strip()
                for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
                if origin.strip()
            ),
            meta_api_enabled=os.getenv("META_API_ENABLED", "false").lower()
            in {"1", "true", "yes"},
            model_api_key=os.getenv("MODEL_API_KEY", "").strip(),
            model_api_base_url=os.getenv(
                "MODEL_API_BASE_URL", "https://api.meta.ai/v1"
            ).strip().rstrip("/"),
            model_api_model=os.getenv("MODEL_API_MODEL", "muse-spark-1.3").strip(),
            meta_api_timeout_seconds=float(os.getenv("META_API_TIMEOUT_SECONDS", "60")),
            meta_api_total_limit=int(os.getenv("META_API_TOTAL_LIMIT", "1")),
        )

    def validate_meta(self) -> None:
        """Network-free preflight; the inference call is the only permitted API request."""
        if not self.meta_api_enabled:
            raise ConfigurationError(
                "Meta inference is disabled. Set META_API_ENABLED=true only after explicit authorization."
            )
        if not self.model_api_key or self.model_api_key == "your_actual_api_key":
            raise ConfigurationError("MODEL_API_KEY is not configured on the server.")
        parsed = urlparse(self.model_api_base_url)
        if parsed.scheme != "https" or parsed.netloc != "api.meta.ai" or parsed.path != "/v1":
            raise ConfigurationError(
                "MODEL_API_BASE_URL must be exactly https://api.meta.ai/v1."
            )
        if self.meta_api_total_limit < 1:
            raise ConfigurationError("META_API_TOTAL_LIMIT must be at least 1.")
        if self.model_api_model != "muse-spark-1.3":
            raise ConfigurationError("MODEL_API_MODEL must be muse-spark-1.3 for this baseline.")

