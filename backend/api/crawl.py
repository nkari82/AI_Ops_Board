from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
import logging
import time
from threading import Lock
from urllib.parse import urlparse

from config import settings
from models import CrawlRequest, YouTubeSearchRequest
from db import get_db
from db_models import CrawledPost
from celery_app import celery_app
from crawlers.github import GithubCrawler
from crawlers.hn import HackerNewsCrawler
from crawlers.youtube import YoutubeCrawler
from services.crawled_post_ingest import CrawledPostIngestService
from services.error_tracker import error_tracker

router = APIRouter(prefix="/crawl", tags=["crawl"])
logger = logging.getLogger(__name__)

# In-memory runtime telemetry for YouTube keyword crawl requests.
# Note: this is process-local runtime telemetry for operational visibility.
_YT_SEARCH_TELEMETRY_LOCK = Lock()
_YT_SEARCH_TELEMETRY: dict[str, Any] = {
    "requested": 0,
    "deduplicated": 0,
    "queued": 0,
    "completed": 0,
    "failed": 0,
    "rate_limited": 0,
    "active_tasks": {},      # task_id -> {query, max_results, pages, status, dedup_key, enqueued_at, enqueued_at_ts, updated_at}
    "active_by_key": {},     # dedup_key -> task_id
    "request_timestamps_by_key": {},  # dedup_key -> [unix_ts, ...]
    "task_summaries": [],    # recent terminal task summaries
    "last_query": None,
    "last_task_id": None,
    "last_status": None,
    "updated_at": None,
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_youtube_search_dedup_key(query: str, max_results: int, pages: int) -> str:
    normalized_query = " ".join((query or "").strip().lower().split())
    return f"{normalized_query}|{max_results}|{pages}"


def _is_active_celery_status(status: str) -> bool:
    return status in {"PENDING", "RECEIVED", "STARTED", "RETRY"}


def _extract_result_count(result: Any) -> int | None:
    if isinstance(result, list):
        return len(result)
    return None


def _cleanup_youtube_search_runtime_locked(now_ts: float | None = None) -> None:
    now_ts = now_ts if now_ts is not None else time.time()
    ttl = max(30, int(getattr(settings, "YOUTUBE_SEARCH_DEDUP_TTL_SECONDS", 900) or 900))

    expired_task_ids: list[str] = []
    for task_id, info in list(_YT_SEARCH_TELEMETRY["active_tasks"].items()):
        enqueued_at_ts = float(info.get("enqueued_at_ts") or 0)
        if enqueued_at_ts > 0 and now_ts - enqueued_at_ts > ttl:
            expired_task_ids.append(task_id)

    for task_id in expired_task_ids:
        info = _YT_SEARCH_TELEMETRY["active_tasks"].pop(task_id, None)
        if not info:
            continue
        dedup_key = info.get("dedup_key")
        if dedup_key and _YT_SEARCH_TELEMETRY["active_by_key"].get(dedup_key) == task_id:
            del _YT_SEARCH_TELEMETRY["active_by_key"][dedup_key]

    window_seconds = max(1, int(getattr(settings, "YOUTUBE_SEARCH_RATE_LIMIT_WINDOW_SECONDS", 60) or 60))
    cutoff = now_ts - window_seconds
    for key in list(_YT_SEARCH_TELEMETRY["request_timestamps_by_key"].keys()):
        timestamps = [ts for ts in _YT_SEARCH_TELEMETRY["request_timestamps_by_key"][key] if ts >= cutoff]
        if timestamps:
            _YT_SEARCH_TELEMETRY["request_timestamps_by_key"][key] = timestamps
        else:
            del _YT_SEARCH_TELEMETRY["request_timestamps_by_key"][key]


def _check_and_record_rate_limit_locked(dedup_key: str, now_ts: float | None = None) -> tuple[bool, int]:
    now_ts = now_ts if now_ts is not None else time.time()
    window_seconds = max(1, int(getattr(settings, "YOUTUBE_SEARCH_RATE_LIMIT_WINDOW_SECONDS", 60) or 60))
    max_requests = max(1, int(getattr(settings, "YOUTUBE_SEARCH_RATE_LIMIT_MAX_REQUESTS", 5) or 5))

    bucket = _YT_SEARCH_TELEMETRY["request_timestamps_by_key"].setdefault(dedup_key, [])
    cutoff = now_ts - window_seconds
    bucket[:] = [ts for ts in bucket if ts >= cutoff]

    if len(bucket) >= max_requests:
        oldest = bucket[0]
        retry_after = max(1, int(window_seconds - (now_ts - oldest)))
        return False, retry_after

    bucket.append(now_ts)
    return True, 0


def _update_youtube_task_status_locked(task_id: str, status: str, result: Any | None = None) -> None:
    task_info = _YT_SEARCH_TELEMETRY["active_tasks"].get(task_id)
    if not task_info:
        return

    previous = task_info.get("status")
    if previous == status:
        return

    task_info["status"] = status
    task_info["updated_at"] = _utc_now_iso()
    _YT_SEARCH_TELEMETRY["last_status"] = status
    _YT_SEARCH_TELEMETRY["updated_at"] = task_info["updated_at"]

    if status in {"SUCCESS", "FAILURE", "REVOKED"}:
        dedup_key = task_info.get("dedup_key")
        if dedup_key and _YT_SEARCH_TELEMETRY["active_by_key"].get(dedup_key) == task_id:
            del _YT_SEARCH_TELEMETRY["active_by_key"][dedup_key]

        result_count = _extract_result_count(result)

        if status == "SUCCESS":
            _YT_SEARCH_TELEMETRY["completed"] += 1
        elif status in {"FAILURE", "REVOKED"}:
            _YT_SEARCH_TELEMETRY["failed"] += 1

        _YT_SEARCH_TELEMETRY["task_summaries"].append(
            {
                "taskId": task_id,
                "query": task_info.get("query"),
                "maxResults": task_info.get("max_results"),
                "pages": task_info.get("pages"),
                "status": status,
                "resultCount": result_count,
                "completedAt": _utc_now_iso(),
            }
        )
        if len(_YT_SEARCH_TELEMETRY["task_summaries"]) > 30:
            _YT_SEARCH_TELEMETRY["task_summaries"] = _YT_SEARCH_TELEMETRY["task_summaries"][-30:]

        del _YT_SEARCH_TELEMETRY["active_tasks"][task_id]


def _register_youtube_search_task(query: str, max_results: int, pages: int, task_id: str, dedup_key: str) -> None:
    with _YT_SEARCH_TELEMETRY_LOCK:
        now = _utc_now_iso()
        _YT_SEARCH_TELEMETRY["requested"] += 1
        _YT_SEARCH_TELEMETRY["queued"] += 1
        _YT_SEARCH_TELEMETRY["last_query"] = query
        _YT_SEARCH_TELEMETRY["last_task_id"] = task_id
        _YT_SEARCH_TELEMETRY["last_status"] = "PENDING"
        _YT_SEARCH_TELEMETRY["updated_at"] = now

        _YT_SEARCH_TELEMETRY["active_by_key"][dedup_key] = task_id
        _YT_SEARCH_TELEMETRY["active_tasks"][task_id] = {
            "query": query,
            "max_results": max_results,
            "pages": pages,
            "status": "PENDING",
            "dedup_key": dedup_key,
            "enqueued_at": now,
            "enqueued_at_ts": time.time(),
            "updated_at": now,
        }


def _record_youtube_search_dedup(task_id: str, query: str) -> None:
    with _YT_SEARCH_TELEMETRY_LOCK:
        _YT_SEARCH_TELEMETRY["requested"] += 1
        _YT_SEARCH_TELEMETRY["deduplicated"] += 1
        _YT_SEARCH_TELEMETRY["last_query"] = query
        _YT_SEARCH_TELEMETRY["last_task_id"] = task_id
        _YT_SEARCH_TELEMETRY["last_status"] = "DEDUP_HIT"
        _YT_SEARCH_TELEMETRY["updated_at"] = _utc_now_iso()


def get_youtube_search_telemetry_snapshot() -> dict[str, Any]:
    from celery.result import AsyncResult

    with _YT_SEARCH_TELEMETRY_LOCK:
        _cleanup_youtube_search_runtime_locked()
        task_ids = list(_YT_SEARCH_TELEMETRY["active_tasks"].keys())

    for task_id in task_ids:
        task_result = AsyncResult(task_id, app=celery_app)
        status = task_result.status
        result_payload = task_result.result if task_result.ready() else None
        with _YT_SEARCH_TELEMETRY_LOCK:
            _update_youtube_task_status_locked(task_id, status, result_payload)

    with _YT_SEARCH_TELEMETRY_LOCK:
        active_tasks = list(_YT_SEARCH_TELEMETRY["active_tasks"].values())
        active_count = len(active_tasks)
        return {
            "requested": _YT_SEARCH_TELEMETRY["requested"],
            "deduplicated": _YT_SEARCH_TELEMETRY["deduplicated"],
            "queued": _YT_SEARCH_TELEMETRY["queued"],
            "completed": _YT_SEARCH_TELEMETRY["completed"],
            "failed": _YT_SEARCH_TELEMETRY["failed"],
            "rateLimited": _YT_SEARCH_TELEMETRY["rate_limited"],
            "activeCount": active_count,
            "activeTasks": active_tasks,
            "recentTaskSummaries": list(_YT_SEARCH_TELEMETRY["task_summaries"]),
            "lastQuery": _YT_SEARCH_TELEMETRY["last_query"],
            "lastTaskId": _YT_SEARCH_TELEMETRY["last_task_id"],
            "lastStatus": _YT_SEARCH_TELEMETRY["last_status"],
            "updatedAt": _YT_SEARCH_TELEMETRY["updated_at"],
        }


def _parse_enabled_sources() -> set[str]:
    raw = (getattr(settings, "CRAWL_ENABLED_SOURCES", "") or "").strip()
    if not raw:
        return {"reddit", "github", "hn", "youtube"}
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _looks_like_placeholder(value: str | None) -> bool:
    text = (value or "").strip().lower()
    if not text:
        return True
    placeholder_markers = ["your_", "changeme", "example", "dummy", "token_here", "api_key_here"]
    return any(marker in text for marker in placeholder_markers)


def _build_crawl_health_snapshot() -> dict[str, Any]:
    enabled = _parse_enabled_sources()

    reddit_rss = bool(getattr(settings, "REDDIT_USE_RSS", True))
    reddit_feeds = (getattr(settings, "REDDIT_RSS_FEEDS", "") or "").strip()
    reddit_client_id = (getattr(settings, "REDDIT_CLIENT_ID", "") or "").strip()
    reddit_client_secret = (getattr(settings, "REDDIT_CLIENT_SECRET", "") or "").strip()

    reddit_status = "disabled"
    reddit_detail = "source disabled"
    if "reddit" in enabled:
        if reddit_rss:
            if reddit_feeds:
                reddit_status, reddit_detail = "healthy", "rss mode enabled"
            else:
                reddit_status, reddit_detail = "degraded", "rss mode enabled but REDDIT_RSS_FEEDS is empty"
        else:
            if not _looks_like_placeholder(reddit_client_id) and not _looks_like_placeholder(reddit_client_secret):
                reddit_status, reddit_detail = "healthy", "api mode configured"
            else:
                reddit_status, reddit_detail = "degraded", "api mode selected but reddit credentials look unset"

    youtube_targets = _parse_youtube_targets()
    youtube_allow_all = bool(getattr(settings, "YOUTUBE_ALLOW_ALL_WHEN_TARGETS_EMPTY", False))
    youtube_search_enabled = bool(getattr(settings, "YOUTUBE_SEARCH_ENABLED", True))

    youtube_status = "disabled"
    youtube_detail = "source disabled"
    if "youtube" in enabled:
        if youtube_search_enabled:
            youtube_status = "healthy"
            youtube_detail = "search enabled"
            if not youtube_allow_all and len(youtube_targets) == 0:
                youtube_detail = "search enabled; direct URL crawl is restricted by empty allow-list"
        else:
            youtube_status = "degraded"
            youtube_detail = "keyword search disabled by YOUTUBE_SEARCH_ENABLED"

    sources = {
        "reddit": {"status": reddit_status, "detail": reddit_detail},
        "github": {
            "status": "healthy" if "github" in enabled else "disabled",
            "detail": "enabled" if "github" in enabled else "source disabled",
        },
        "hn": {
            "status": "healthy" if "hn" in enabled else "disabled",
            "detail": "enabled" if "hn" in enabled else "source disabled",
        },
        "youtube": {
            "status": youtube_status,
            "detail": youtube_detail,
        },
    }

    overall = "healthy"
    source_statuses = [item["status"] for item in sources.values()]
    if any(s == "degraded" for s in source_statuses):
        overall = "degraded"
    if all(s == "disabled" for s in source_statuses):
        overall = "disabled"

    return {
        "status": overall,
        "sources": sources,
        "timestamp": _utc_now_iso(),
    }


def _ensure_source_enabled(source_name: str) -> None:
    enabled = _parse_enabled_sources()
    if source_name.lower() not in enabled:
        raise HTTPException(
            status_code=403,
            detail=f"Crawl source '{source_name}' is disabled by CRAWL_ENABLED_SOURCES",
        )


def _parse_youtube_targets() -> list[str]:
    raw = (getattr(settings, "YOUTUBE_TARGET_URLS", "") or "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _normalize_youtube_url(url: str) -> str:
    parsed = urlparse((url or "").strip())
    if not parsed.scheme:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{parsed.query}".rstrip("?")


def _is_allowed_youtube_url(url: str) -> bool:
    allowed = {_normalize_youtube_url(item) for item in _parse_youtube_targets()}
    allowed.discard("")
    if not allowed:
        return bool(getattr(settings, "YOUTUBE_ALLOW_ALL_WHEN_TARGETS_EMPTY", False))
    return _normalize_youtube_url(url) in allowed

@celery_app.task
def background_crawl_reddit_task(subreddit: str, limit: int):
    import asyncio
    import httpx
    from crawlers.reddit import RedditCrawler
    from db import async_session_maker
    from services.crawled_post_ingest import CrawledPostIngestService
    
    # Broadcast start
    asyncio.run(httpx.AsyncClient().post("http://backend:8000/api/ws/broadcast", json={"message": f"Crawl started for {subreddit}"}))
    
    async def _run():
        crawler = RedditCrawler()
        results = await crawler.crawl(subreddit, limit)
        async with async_session_maker() as db:
            service = CrawledPostIngestService()
            await service.ingest_items(db, results, source_name="reddit", context={"subreddit": subreddit})
            await db.commit()
        return results
    
    result = asyncio.run(_run())
    logger.info("Reddit background crawl done subreddit=%s items=%s", subreddit, len(result or []))
    
    # Broadcast finish
    asyncio.run(httpx.AsyncClient().post("http://backend:8000/api/ws/broadcast", json={"message": f"Crawl finished for {subreddit}"}))
    
    return result

@celery_app.task
def background_crawl_youtube_task(url: str):
    import asyncio
    from crawlers.youtube import YoutubeCrawler
    from db import async_session_maker
    from services.knowledge_manager import KnowledgeManager
    from services.crawled_post_ingest import CrawledPostIngestService
    
    async def _run():
        crawler = YoutubeCrawler()
        result = await crawler.crawl(url)
        if result:
            async with async_session_maker() as db:
                service = CrawledPostIngestService()
                posts = await service.ingest_items(db, [result], source_name="youtube", context={"url": url})
                await db.commit()
                if posts:
                    km = KnowledgeManager()
                    await km.generate_knowledge_cards(db, new_post=posts[0])
                
        return result
    
    # Celery 환경에서 루프 충돌을 피하기 위해 asyncio.run 대신 내부에서 동기적 실행
    result = asyncio.run(_run())
    logger.info("YouTube background crawl done url=%s success=%s", url, bool(result))
    return result


@celery_app.task
def background_crawl_youtube_search_task(query: str, max_results: int = 8, pages: int = 2):
    import asyncio
    from crawlers.youtube import YoutubeCrawler
    from db import async_session_maker
    from services.knowledge_manager import KnowledgeManager
    from services.crawled_post_ingest import CrawledPostIngestService

    async def _run():
        crawler = YoutubeCrawler()
        results = await crawler.crawl_search(query=query, max_videos=max_results, pages=pages)
        if not results:
            return []

        async with async_session_maker() as db:
            service = CrawledPostIngestService()
            posts = await service.ingest_items(db, results, source_name="youtube", context={"query": query})
            await db.commit()

            if posts:
                km = KnowledgeManager()
                for post in posts:
                    await km.generate_knowledge_cards(db, new_post=post)

        return results

    results = asyncio.run(_run())
    logger.info(
        "YouTube keyword crawl done query=%s requested=%s pages=%s collected=%s",
        query,
        max_results,
        pages,
        len(results or []),
    )
    return results

def detect_domain(text: str) -> str:
    text = text.lower()
    if 'unity' in text: return 'Unity'
    if 'unreal' in text: return 'Unreal'
    if 'react' in text or 'frontend' in text: return '프론트엔드'
    if 'python' in text or 'backend' in text: return '백엔드'
    return '기타'
@router.get("/health")
async def crawl_health():
    return _build_crawl_health_snapshot()


@router.post("/reddit")
async def crawl_reddit(request: CrawlRequest, db: AsyncSession = Depends(get_db)):
    _ensure_source_enabled("reddit")
    subreddit = request.subreddit or "LocalLLaMA"
    task = background_crawl_reddit_task.delay(subreddit, request.limit)
    return {"task_id": task.id, "message": "Crawl task started", "subreddit": subreddit}

@router.post("/youtube")
async def crawl_youtube(request: Dict[str, str]):
    _ensure_source_enabled("youtube")
    url = request.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL required")
    if not _is_allowed_youtube_url(url):
        raise HTTPException(status_code=403, detail="URL is not allowed by YOUTUBE_TARGET_URLS")
    task = background_crawl_youtube_task.delay(url)
    return {"task_id": task.id, "message": "YouTube crawl task started", "url": url}


@router.post("/youtube/search")
async def crawl_youtube_search(request: YouTubeSearchRequest):
    _ensure_source_enabled("youtube")

    if not bool(getattr(settings, "YOUTUBE_SEARCH_ENABLED", True)):
        raise HTTPException(status_code=403, detail="YouTube keyword search is disabled by YOUTUBE_SEARCH_ENABLED")

    query = (request.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    max_limit = max(1, int(getattr(settings, "YOUTUBE_SEARCH_MAX_RESULTS", 8) or 8))
    max_pages_limit = max(1, int(getattr(settings, "YOUTUBE_SEARCH_MAX_PAGES", 2) or 2))

    max_results = max(1, min(int(request.max_results or 1), max_limit))
    pages = max(1, min(int(request.pages or 1), max_pages_limit))

    from celery.result import AsyncResult

    dedup_key = _build_youtube_search_dedup_key(query, max_results, pages)

    with _YT_SEARCH_TELEMETRY_LOCK:
        _cleanup_youtube_search_runtime_locked()
        is_allowed, retry_after = _check_and_record_rate_limit_locked(dedup_key)
        if not is_allowed:
            _YT_SEARCH_TELEMETRY["requested"] += 1
            _YT_SEARCH_TELEMETRY["rate_limited"] += 1
            _YT_SEARCH_TELEMETRY["last_query"] = query
            _YT_SEARCH_TELEMETRY["last_status"] = "RATE_LIMITED"
            _YT_SEARCH_TELEMETRY["updated_at"] = _utc_now_iso()
            raise HTTPException(
                status_code=429,
                detail=f"YouTube keyword crawl is rate-limited for this query. retry_after={retry_after}s",
            )

        existing_task_id = _YT_SEARCH_TELEMETRY["active_by_key"].get(dedup_key)

    if existing_task_id:
        existing_status = AsyncResult(existing_task_id, app=celery_app).status
        with _YT_SEARCH_TELEMETRY_LOCK:
            _update_youtube_task_status_locked(existing_task_id, existing_status)

        if _is_active_celery_status(existing_status):
            _record_youtube_search_dedup(existing_task_id, query)
            return {
                "task_id": existing_task_id,
                "message": "YouTube keyword crawl task already in progress (deduplicated)",
                "query": query,
                "max_results": max_results,
                "pages": pages,
                "deduplicated": True,
                "status": existing_status,
            }

    task = background_crawl_youtube_search_task.delay(query, max_results, pages)
    _register_youtube_search_task(query, max_results, pages, task.id, dedup_key)
    return {
        "task_id": task.id,
        "message": "YouTube keyword crawl task started",
        "query": query,
        "max_results": max_results,
        "pages": pages,
        "deduplicated": False,
        "status": "PENDING",
    }


@router.post("/youtube/from-env")
async def crawl_youtube_from_env():
    _ensure_source_enabled("youtube")
    targets = _parse_youtube_targets()
    if not targets:
        raise HTTPException(status_code=400, detail="YOUTUBE_TARGET_URLS is empty")

    task_ids: list[str] = []
    for url in targets:
        task = background_crawl_youtube_task.delay(url)
        task_ids.append(task.id)

    return {
        "message": "YouTube crawl tasks started from env list",
        "count": len(task_ids),
        "task_ids": task_ids,
        "targets": targets,
    }


@router.get("/status/{task_id}")
async def get_crawl_status(task_id: str):
    from celery.result import AsyncResult

    task_result = AsyncResult(task_id, app=celery_app)
    status = task_result.status

    result_payload = task_result.result if task_result.ready() else None

    with _YT_SEARCH_TELEMETRY_LOCK:
        _update_youtube_task_status_locked(task_id, status, result_payload)

    return {
        "task_id": task_id,
        "status": status,
        "result": task_result.result if task_result.ready() else None
    }


@router.post("/github")
async def crawl_github(limit: int = 10, db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    _ensure_source_enabled("github")
    try:
        crawler = GithubCrawler()
        service = CrawledPostIngestService()
        
        results = await crawler.crawl_trending(limit)
        await service.ingest_items(db, results, source_name="github")
        return results
    except Exception as e:
        error_tracker.log_error("CRAWL_FAILURE", str(e), details={"source": "github", "limit": limit})
        raise HTTPException(status_code=500, detail=f"GitHub crawl failed: {str(e)}")


@router.post("/hn")
async def crawl_hackernews(limit: int = 10, db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    _ensure_source_enabled("hn")
    try:
        logger.info(f"Starting HackerNews crawl with limit={limit}")
        crawler = HackerNewsCrawler()
        service = CrawledPostIngestService()
        
        results = await crawler.crawl_top_stories(limit)
        logger.info(f"HackerNews crawl finished. Fetched {len(results)} items.")
        await service.ingest_items(db, results, source_name="hn")
        logger.info("Successfully committed HackerNews posts to DB.")
        return results
    except Exception as e:
        logger.error(f"Hacker News crawl failed with limit={limit}: {e}", exc_info=True)
        error_tracker.log_error("CRAWL_FAILURE", str(e), details={"source": "hn", "limit": limit})
        raise HTTPException(status_code=500, detail=f"Hacker News crawl failed: {str(e)}")


@router.get("/posts")
async def get_crawled_posts(
    source: str = None,
    domain: str = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    query = select(CrawledPost).order_by(CrawledPost.score.desc())
    
    if source:
        query = query.where(CrawledPost.source.like(f"%{source}%"))
    if domain:
        query = query.where(CrawledPost.domain == domain)
    
    result = await db.execute(query.offset(skip).limit(limit))
    posts = result.scalars().all()
    
    return [
        {
            "id": p.id,
            "title": p.title,
            "url": p.url,
            "source": p.source,
            "score": p.score,
            "domain": p.domain,
            "created_at": p.created_at.isoformat() if p.created_at else None
        }
        for p in posts
    ]
