from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
from models import CrawlRequest
from db import get_db
from db_models import CrawledPost
from celery_app import celery_app

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



def detect_domain(title: str, content: str = "") -> str:
    text = f"{title} {content}".lower()
    if any(w in text for w in ["unity", "unreal", "game engine", "godot"]):
        return "게임 엔진"
    if any(w in text for w in ["react", "vue", "angular", "next.js", "frontend", "css"]):
        return "프론트엔드"
    if any(w in text for w in ["python", "fastapi", "django", "node", "api", "backend"]):
        return "백엔드"
    if any(w in text for w in ["llm", "vllm", "gpt", "model", "inference", "localai"]):
        return "로컬 LLM"
    if any(w in text for w in ["mcp", "agent", "claude", "opencode", "cursor"]):
        return "Agent/MCP"
    return "기타"


@router.post("/reddit")
async def crawl_reddit(request: CrawlRequest, db: AsyncSession = Depends(get_db)):
    subreddit = request.subreddit or "LocalLLaMA"
    task = background_crawl_reddit_task.delay(subreddit, request.limit)
    return {"task_id": task.id, "message": "Crawl task started", "subreddit": subreddit}

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
        from ..crawlers.github import GithubCrawler
        crawler = GithubCrawler()
        
        results = await crawler.crawl_trending(limit)
        
        for item in results:
            post = CrawledPost(
                title=item.get("name", ""),
                url=item.get("html_url", ""),
                source="github:trending",
                source_type="github",
                content=item.get("description", ""),
                score=item.get("stargazers_count", 0),
                metadata={"language": item.get("language"), "topics": item.get("topics")},
                domain=detect_domain(item.get("description", ""))
            )
            db.add(post)
        
        await db.commit()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub crawl failed: {str(e)}")


@router.post("/hn")
async def crawl_hackernews(limit: int = 10, db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    try:
        from ..crawlers.hn import HackerNewsCrawler
        crawler = HackerNewsCrawler()
        
        results = await crawler.crawl_top_stories(limit)
        
        for item in results:
            post = CrawledPost(
                title=item.get("title", ""),
                url=item.get("link", ""),
                source="hackernews:top",
                source_type="hn",
                content="",
                score=item.get("score", 0),
                metadata={"by": item.get("by"), "comments_count": item.get("comments_count")},
                domain=detect_domain(item.get("title", ""))
            )
            db.add(post)
        
        await db.commit()
        return results
    except Exception as e:
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