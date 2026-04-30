from __future__ import annotations

from importlib import import_module
from typing import Any, cast

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _load_runtime_dependencies() -> tuple[Any, Any, Any, Any, Any]:
    try:
        db_module = import_module("backend.db")
        quality_module = import_module("backend.services.data_quality_monitor")
        tracker_module = import_module("backend.services.error_tracker")
        crawl_module = import_module("backend.api.crawl")
        models_module = import_module("backend.db_models")
    except ModuleNotFoundError:
        db_module = import_module("db")
        quality_module = import_module("services.data_quality_monitor")
        tracker_module = import_module("services.error_tracker")
        crawl_module = import_module("api.crawl")
        models_module = import_module("db_models")
    return (
        db_module.get_db,
        quality_module.DataQualityMonitor,
        tracker_module.error_tracker,
        crawl_module.get_youtube_search_telemetry_snapshot,
        models_module.CrawledPost,
    )


get_db, DataQualityMonitor, error_tracker, get_youtube_search_telemetry_snapshot, CrawledPost = _load_runtime_dependencies()
get_db = cast(Any, get_db)
DataQualityMonitor = cast(Any, DataQualityMonitor)
error_tracker = cast(Any, error_tracker)
get_youtube_search_telemetry_snapshot = cast(Any, get_youtube_search_telemetry_snapshot)
CrawledPost = cast(Any, CrawledPost)

router = APIRouter(prefix="/admin", tags=["admin"])

quality_monitor = DataQualityMonitor()


@router.get("/errors")
async def get_errors(limit: int = Query(100, ge=1, le=1000)):
    return {
        "items": error_tracker.recent(limit),
        "summary": error_tracker.summary(),
    }


@router.get("/data-quality")
async def get_data_quality(db: AsyncSession = Depends(get_db)):
    return await quality_monitor.get_quality_metrics(db)


def _normalize_youtube_metrics(youtube_search: dict[str, Any]) -> dict[str, Any]:
    active_tasks = youtube_search.get("activeTasks", [])
    recent_summaries = youtube_search.get("recentTaskSummaries", [])

    return {
        "requested": int(youtube_search.get("requested", 0) or 0),
        "deduplicated": int(youtube_search.get("deduplicated", 0) or 0),
        "queued": int(youtube_search.get("queued", 0) or 0),
        "completed": int(youtube_search.get("completed", 0) or 0),
        "failed": int(youtube_search.get("failed", 0) or 0),
        "rateLimited": int(youtube_search.get("rateLimited", 0) or 0),
        "activeCount": int(youtube_search.get("activeCount", 0) or 0),
        "activeTasks": active_tasks if isinstance(active_tasks, list) else [],
        "recentTaskSummaries": recent_summaries if isinstance(recent_summaries, list) else [],
        "lastQuery": youtube_search.get("lastQuery"),
        "lastTaskId": youtube_search.get("lastTaskId"),
        "lastStatus": youtube_search.get("lastStatus"),
        "updatedAt": youtube_search.get("updatedAt"),
    }


def _aggregate_rss_quality(extra_data_rows: list[Any]) -> dict[str, Any]:
    accepted_total = 0
    skipped_total = 0
    extracted_total = 0
    entry_blocks_total = 0
    by_reason: dict[str, int] = {}

    for row in extra_data_rows:
        if not isinstance(row, dict):
            continue
        rss_quality = row.get("rss_quality")
        if not isinstance(rss_quality, dict):
            continue

        extracted_total += int(rss_quality.get("extractedLinks", 0) or 0)
        accepted_total += int(rss_quality.get("acceptedLinks", 0) or 0)
        entry_blocks_total += int(rss_quality.get("entryBlocks", 0) or 0)

        skipped_links = rss_quality.get("skippedLinks")
        if isinstance(skipped_links, list):
            skipped_total += len(skipped_links)
            for item in skipped_links:
                if not isinstance(item, dict):
                    continue
                reason = item.get("reason")
                if not isinstance(reason, str) or not reason:
                    continue
                by_reason[reason] = by_reason.get(reason, 0) + 1

    considered = accepted_total + skipped_total
    acceptance_rate = round(accepted_total / considered, 4) if considered > 0 else None

    return {
        "entryBlocksTotal": entry_blocks_total,
        "extractedLinksTotal": extracted_total,
        "acceptedLinksTotal": accepted_total,
        "skippedLinksTotal": skipped_total,
        "acceptanceRate": acceptance_rate,
        "skippedByReason": by_reason,
    }


@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)):
    quality = await quality_monitor.get_quality_metrics(db)
    errors = error_tracker.summary()
    youtube_search = _normalize_youtube_metrics(get_youtube_search_telemetry_snapshot())

    rss_rows = await db.scalars(
        select(CrawledPost.extra_data).where(CrawledPost.source_type == "reddit")
    )
    rss_quality = _aggregate_rss_quality(list(rss_rows))

    return {
        "quality": quality,
        "errors": errors,
        "youtubeSearch": youtube_search,
        "rssQuality": rss_quality,
    }
