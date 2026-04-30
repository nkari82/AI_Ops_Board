from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from backend.db_models import CrawledPost
except ModuleNotFoundError:
    from db_models import CrawledPost

_CACHE_PATH = Path(__file__).resolve().parents[1] / "data" / "recommendation_settings_cache.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_cached_settings() -> dict[str, Any] | None:
    if not _CACHE_PATH.exists():
        return None
    try:
        payload = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def save_cached_settings(*, settings: list[dict[str, Any]], generated_by: str, latest_post_updated_at: str | None) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": _utc_now_iso(),
        "generated_by": generated_by,
        "latest_post_updated_at": latest_post_updated_at,
        "settings": settings,
    }
    _CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


async def get_latest_post_updated_at(db: AsyncSession) -> str | None:
    value = await db.scalar(select(CrawledPost.updated_at).order_by(CrawledPost.updated_at.desc()).limit(1))
    if not value:
        return None
    try:
        return value.astimezone(timezone.utc).isoformat()
    except Exception:
        return str(value)


def is_cache_fresh(cache_payload: dict[str, Any] | None, latest_post_updated_at: str | None) -> bool:
    if not cache_payload:
        return False
    cached_marker = cache_payload.get("latest_post_updated_at")
    if not isinstance(cached_marker, str):
        return False
    if latest_post_updated_at is None:
        return True
    return cached_marker == latest_post_updated_at
