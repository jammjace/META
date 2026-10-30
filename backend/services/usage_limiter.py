from __future__ import annotations

import json
from pathlib import Path
from threading import Lock


class ApiLimitReachedError(RuntimeError):
    pass


class ApiUsageLimiter:
    _lock = Lock()

    def __init__(self, storage: Path, limit: int) -> None:
        self.path = storage / "api_usage.json"
        self.limit = limit

    def reserve(self) -> int:
        """Reserve before the call; failures still consume the testing allowance."""
        with self._lock:
            used = 0
            if self.path.exists():
                used = int(json.loads(self.path.read_text(encoding="utf-8")).get("used", 0))
            if used >= self.limit:
                raise ApiLimitReachedError(
                    f"Meta API testing limit reached ({used}/{self.limit})."
                )
            self.path.parent.mkdir(parents=True, exist_ok=True)
            used += 1
            self.path.write_text(json.dumps({"used": used, "limit": self.limit}, indent=2), encoding="utf-8")
            return used

