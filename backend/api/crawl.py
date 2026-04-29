from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
import logging
from urllib.parse import urlparse

from config import settings
from models import CrawlRequest
from db import get_db
from db_models import CrawledPost
from celery_app import celery_app
from crawlers.github import GithubCrawler
from crawlers.hn import HackerNewsCrawler
from crawlers.youtube import YoutubeCrawler
from services.crawled_post_ingest import CrawledPostIngestService

router = APIRouter(prefix="/crawl", tags=["crawl"])
logger = logging.getLogger(__name__)


def _parse_enabled_sources() -> set[str]:
    raw = (getattr(settings, "CRAWL_ENABLED_SOURCES", "") or "").strip()
    if not raw:
        return {"reddit", "github", "hn", "youtube"}
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


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
        # if list is empty, treat as unrestricted
        return True
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
    return asyncio.run(_run())

def detect_domain(text: str) -> str:
    text = text.lower()
    if 'unity' in text: return 'Unity'
    if 'unreal' in text: return 'Unreal'
    if 'react' in text or 'frontend' in text: return '프론트엔드'
    if 'python' in text or 'backend' in text: return '백엔드'
    return '기타'
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
    return {
        "task_id": task_id,
        "status": task_result.status,
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
