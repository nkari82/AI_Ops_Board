from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime

from db import get_db
from db_models import CrawledPost
from models import OperationPost, Domain, BoardCategory, SourceKind

router = APIRouter(prefix="/operation-posts", tags=["posts"])

@router.get("", response_model=List[OperationPost])
async def get_operation_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CrawledPost).order_by(CrawledPost.created_at.desc()).offset(skip).limit(limit))
    posts = result.scalars().all()
    
    return [
        OperationPost(
            id=p.id,
            title=p.title,
            category=BoardCategory.실전_운용, # Default mapping
            domain=Domain.기타, # Needs robust mapping based on p.domain
            score=p.score or 0,
            source_kind=SourceKind.crawled,
            sources=[p.url],
            updated_at=p.updated_at or datetime.now(),
            summary=p.content[:200] if p.content else "",
            action="크롤링된 지식 확인",
            tags=p.tags or []
        )
        for p in posts
    ]


@router.get("/{post_id}", response_model=OperationPost)
async def get_operation_post(
    post_id: int,
    db: AsyncSession = Depends(get_db)
):
    post = next((p for p in MOCK_POSTS if p.id == post_id), None)
    if not post:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Post not found")
    return post
