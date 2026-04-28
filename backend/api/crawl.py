from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.dialects.postgresql import insert
from typing import List, Dict, Any
import logging
from models import CrawlRequest
from db import get_db
from db_models import CrawledPost
from celery_app import celery_app
from crawlers.github import GithubCrawler
from crawlers.hn import HackerNewsCrawler
from crawlers.youtube import YoutubeCrawler

router = APIRouter(prefix="/crawl", tags=["crawl"])
logger = logging.getLogger(__name__)

@celery_app.task
def background_crawl_reddit_task(subreddit: str, limit: int):
    import asyncio
    import httpx
    from crawlers.reddit import RedditCrawler
    
    # Broadcast start
    asyncio.run(httpx.AsyncClient().post("http://backend:8000/api/ws/broadcast", json={"message": f"Crawl started for {subreddit}"}))
    
    async def _run():
        crawler = RedditCrawler()
        return await crawler.crawl(subreddit, limit)
    
    result = asyncio.run(_run())
    
    # Broadcast finish
    asyncio.run(httpx.AsyncClient().post("http://backend:8000/api/ws/broadcast", json={"message": f"Crawl finished for {subreddit}"}))
    
    return result

@celery_app.task
def background_crawl_youtube_task(url: str):
    import asyncio
    import httpx
    from sqlalchemy.ext.asyncio import AsyncSession
    from db import async_session_factory
    from db_models import CrawledPost
    from services.knowledge_manager import KnowledgeManager
    
    # Broadcast start
    asyncio.run(httpx.AsyncClient().post("http://backend:8000/api/ws/broadcast", json={"message": f"Crawl started for YouTube: {url}"}))
    
    async def _run():
        crawler = YoutubeCrawler()
        result = await crawler.crawl(url)
        if result:
            async with async_session_factory() as db:
                post = CrawledPost(
                    title=result["title"],
                    url=result["url"],
                    source=f"youtube:{url}",
                    source_type="youtube",
                    content=result["content"],
                    score=0,
                    extra_data={},
                    domain="기타"
                )
                db.add(post)
                await db.commit()
                await db.refresh(post)
                
                # AI 분석 파이프라인 연동
                km = KnowledgeManager()
                await km.generate_knowledge_cards(db, new_post=post)
                
        return result
    
    result = asyncio.run(_run())
    
    # Broadcast finish
    asyncio.run(httpx.AsyncClient().post("http://backend:8000/api/ws/broadcast", json={"message": f"Crawl finished for YouTube: {url}"}))
    
    return result

def detect_domain(text: str) -> str:
    text = text.lower()
    if 'unity' in text: return 'Unity'
    if 'unreal' in text: return 'Unreal'
    if 'react' in text or 'frontend' in text: return '프론트엔드'
    if 'python' in text or 'backend' in text: return '백엔드'
    return '기타'
@router.post("/reddit")
async def crawl_reddit(request: CrawlRequest, db: AsyncSession = Depends(get_db)):
    subreddit = request.subreddit or "LocalLLaMA"
    task = background_crawl_reddit_task.delay(subreddit, request.limit)
    return {"task_id": task.id, "message": "Crawl task started", "subreddit": subreddit}

@router.post("/youtube")
async def crawl_youtube(request: Dict[str, str]):
    url = request.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL required")
    task = background_crawl_youtube_task.delay(url)
    return {"task_id": task.id, "message": "YouTube crawl task started"}


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
    try:
        crawler = GithubCrawler()
        
        results = await crawler.crawl_trending(limit)
        
        for item in results:
            stmt = insert(CrawledPost).values(
                title=item.get("name", ""),
                url=item.get("html_url", ""),
                source="github:trending",
                source_type="github",
                content=item.get("description", ""),
                score=item.get("stargazers_count", 0),
                extra_data={"language": item.get("language"), "topics": item.get("topics")},
                domain=detect_domain(item.get("description", ""))
            )
            stmt = stmt.on_conflict_do_update(
                constraint='uix_crawled_post_url',
                set_={
                    "title": stmt.excluded.title,
                    "content": stmt.excluded.content,
                    "score": stmt.excluded.score,
                    "extra_data": stmt.excluded.extra_data,
                }
            )
            await db.execute(stmt)
        
        await db.commit()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub crawl failed: {str(e)}")


@router.post("/hn")
async def crawl_hackernews(limit: int = 10, db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    try:
        logger.info(f"Starting HackerNews crawl with limit={limit}")
        crawler = HackerNewsCrawler()
        
        results = await crawler.crawl_top_stories(limit)
        logger.info(f"HackerNews crawl finished. Fetched {len(results)} items.")
        
        for item in results:
            stmt = insert(CrawledPost).values(
                title=item.get("title", ""),
                url=item.get("link", ""),
                source="hackernews:top",
                source_type="hn",
                content="",
                score=item.get("score", 0),
                extra_data={"by": item.get("by"), "comments_count": item.get("comments_count")},
                domain=detect_domain(item.get("title", ""))
            )
            stmt = stmt.on_conflict_do_update(
                constraint='uix_crawled_post_url',
                set_={
                    "title": stmt.excluded.title,
                    "content": stmt.excluded.content,
                    "score": stmt.excluded.score,
                    "extra_data": stmt.excluded.extra_data,
                }
            )
            await db.execute(stmt)
        
        await db.commit()
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