from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any


class ErrorTracker:
    def __init__(self, max_entries: int = 1000):
        self._entries: deque[dict[str, Any]] = deque(maxlen=max_entries)
        self._lock = Lock()

    def log_error(
        self,
        category: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        level: str = "error",
    ) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "message": message,
            "level": level,
            "details": details or {},
        }
        with self._lock:
            self._entries.appendleft(entry)

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 1000))
        with self._lock:
            return list(self._entries)[:safe_limit]

    def summary(self) -> dict[str, Any]:
        with self._lock:
            total = len(self._entries)
            by_category: dict[str, int] = {}
            for item in self._entries:
                cat = item.get("category", "unknown")
                by_category[cat] = by_category.get(cat, 0) + 1

        return {
            "total": total,
            "by_category": by_category,
        }


error_tracker = ErrorTracker()
