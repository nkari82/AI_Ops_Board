from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from importlib import import_module
from typing import Any, cast

from fastapi import APIRouter
from sqlalchemy import text


def _load_runtime_dependencies() -> tuple[Any, Any, Any, Any, Any]:
    try:
        db_module = import_module("backend.db")
        tracker_module = import_module("backend.services.error_tracker")
        crawl_module = import_module("backend.api.crawl")
        config_module = import_module("backend.config")
        celery_module = import_module("backend.celery_app")
    except ModuleNotFoundError:
        db_module = import_module("db")
        tracker_module = import_module("services.error_tracker")
        crawl_module = import_module("api.crawl")
        config_module = import_module("config")
        celery_module = import_module("celery_app")
    return (
        db_module.async_session_maker,
        tracker_module.error_tracker,
        crawl_module.get_youtube_search_telemetry_snapshot,
        config_module.settings,
        celery_module.celery_app,
    )


async_session_maker, error_tracker, get_youtube_search_telemetry_snapshot, settings, celery_app = _load_runtime_dependencies()
async_session_maker = cast(Any, async_session_maker)
error_tracker = cast(Any, error_tracker)
get_youtube_search_telemetry_snapshot = cast(Any, get_youtube_search_telemetry_snapshot)
settings = cast(Any, settings)
celery_app = cast(Any, celery_app)

router = APIRouter(prefix="/health", tags=["health"])


async def _check_db() -> dict[str, Any]:
    try:
        async with async_session_maker() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as exc:
        error_tracker.log_error("DB_ERROR", str(exc), details={"check": "health_db"})
        return {"status": "unhealthy", "error": str(exc)}


async def _check_redis() -> dict[str, Any]:
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        return {"status": "degraded", "reason": "REDIS_URL_NOT_SET"}

    client = None
    try:
        redis_asyncio = import_module("redis.asyncio")
        client = redis_asyncio.from_url(redis_url, socket_connect_timeout=1.5, socket_timeout=1.5)
        pong = await client.ping()
        return {"status": "healthy" if pong else "degraded", "pong": bool(pong)}
    except Exception as exc:
        error_tracker.log_error("REDIS_ERROR", str(exc), details={"check": "health_redis"})
        return {"status": "unhealthy", "error": str(exc)}
    finally:
        if client is not None:
            await client.aclose()


async def _check_celery() -> dict[str, Any]:
    try:
        inspect = celery_app.control.inspect(timeout=1)
        ping_result = await asyncio.wait_for(asyncio.to_thread(inspect.ping), timeout=2)
        workers = sorted((ping_result or {}).keys()) if isinstance(ping_result, dict) else []
        if workers:
            return {"status": "healthy", "workers": workers}
        return {"status": "degraded", "reason": "NO_WORKER_PING"}
    except Exception as exc:
        error_tracker.log_error("CELERY_ERROR", str(exc), details={"check": "health_celery"})
        return {"status": "unhealthy", "error": str(exc)}


def _check_llm_config() -> dict[str, Any]:
    configured = []
    if getattr(settings, "GOOGLE_AI_STUDIO_KEY", None):
        configured.append("gemini")
    if getattr(settings, "POLLINATIONS_API_KEY", None):
        configured.append("pollinations")
    if getattr(settings, "GROQ_API_KEY", None):
        configured.append("groq")
    if getattr(settings, "OPENROUTER_API_KEY", None):
        configured.append("openrouter")
    if getattr(settings, "HUGGINGFACE_TOKEN", None):
        configured.append("huggingface")

    if configured:
        return {
            "status": "healthy",
            "configuredProviders": configured,
            "failoverEnabled": bool(getattr(settings, "LLM_FAILOVER_ENABLED", True)),
        }

    return {
        "status": "degraded",
        "configuredProviders": [],
        "failoverEnabled": bool(getattr(settings, "LLM_FAILOVER_ENABLED", True)),
        "reason": "NO_PROVIDER_KEY",
    }


def _normalize_youtube_health(youtube_search: dict[str, Any]) -> dict[str, Any]:
    return {
        "requested": int(youtube_search.get("requested", 0) or 0),
        "deduplicated": int(youtube_search.get("deduplicated", 0) or 0),
        "activeCount": int(youtube_search.get("activeCount", 0) or 0),
        "queued": int(youtube_search.get("queued", 0) or 0),
        "completed": int(youtube_search.get("completed", 0) or 0),
        "failed": int(youtube_search.get("failed", 0) or 0),
        "rateLimited": int(youtube_search.get("rateLimited", 0) or 0),
        "lastStatus": youtube_search.get("lastStatus"),
        "updatedAt": youtube_search.get("updatedAt"),
    }


@router.get("")
async def health_basic() -> dict[str, Any]:
    db_result = await _check_db()
    redis_result = await _check_redis()
    celery_result = await _check_celery()
    llm_result = _check_llm_config()

    statuses = [db_result.get("status"), redis_result.get("status"), celery_result.get("status"), llm_result.get("status")]
    if "unhealthy" in statuses:
        overall = "unhealthy"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "status": overall,
        "service": "ai-ops-board-backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "database": db_result,
            "redis": redis_result,
            "celery": celery_result,
            "llm": llm_result,
        },
    }


def _compute_slo_breached(youtube_health: dict[str, Any]) -> bool:
    requested = int(youtube_health.get("requested", 0) or 0)
    failed = int(youtube_health.get("failed", 0) or 0)
    rate_limited = int(youtube_health.get("rateLimited", 0) or 0)

    if failed >= 3:
        return True
    if rate_limited >= 3:
        return True
    if requested >= 10 and failed / max(1, requested) >= 0.3:
        return True
    return False


def _compute_consistency_warning(youtube_health: dict[str, Any]) -> dict[str, Any]:
    requested = int(youtube_health.get("requested", 0) or 0)
    queued = int(youtube_health.get("queued", 0) or 0)
    active = int(youtube_health.get("activeCount", 0) or 0)
    completed = int(youtube_health.get("completed", 0) or 0)
    failed = int(youtube_health.get("failed", 0) or 0)

    terminal = completed + failed
    accounted = terminal + active

    warnings: list[str] = []
    if requested > 0 and accounted > requested + queued:
        warnings.append("ACCOUNTED_GT_REQUESTED")
    if min(requested, queued, active, completed, failed) < 0:
        warnings.append("NEGATIVE_COUNTER_DETECTED")
    if terminal > requested + queued:
        warnings.append("TERMINAL_GT_INFLOW")

    return {
        "ok": len(warnings) == 0,
        "warnings": warnings,
        "requested": requested,
        "queued": queued,
        "active": active,
        "completed": completed,
        "failed": failed,
    }


@router.get("/detailed")
async def health_detailed() -> dict[str, Any]:
    db_result = await _check_db()
    redis_result = await _check_redis()
    celery_result = await _check_celery()
    llm_result = _check_llm_config()
    youtube_search = get_youtube_search_telemetry_snapshot()
    youtube_health = _normalize_youtube_health(youtube_search)

    statuses = [db_result.get("status"), redis_result.get("status"), celery_result.get("status"), llm_result.get("status")]
    if "unhealthy" in statuses:
        status = "unhealthy"
    elif "degraded" in statuses:
        status = "degraded"
    else:
        status = "healthy"

    if youtube_health["failed"] > 0 and youtube_health["activeCount"] == 0:
        # Surface runtime stress as degraded for operators when failures accumulated.
        status = "degraded" if status == "healthy" else status

    slo_breached = _compute_slo_breached(youtube_health)
    consistency = _compute_consistency_warning(youtube_health)
    if slo_breached and status == "healthy":
        status = "degraded"
    if not consistency.get("ok", True) and status == "healthy":
        status = "degraded"

    return {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sloBreached": slo_breached,
        "checks": {
            "database": db_result,
            "redis": redis_result,
            "celery": celery_result,
            "llm": llm_result,
            "errors": error_tracker.summary(),
            "youtubeSearch": youtube_health,
            "consistency": consistency,
        },
    }
