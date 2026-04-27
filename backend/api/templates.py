from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db import get_db
from db_models import CrawledPost
from services.template_manager import TemplateManager

router = APIRouter(prefix="/templates", tags=["templates"])

@router.post("/generate")
async def generate_template(domain: str, db: AsyncSession = Depends(get_db)):
    # 1. 해당 domain의 지식 데이터를 가져옴
    query = select(CrawledPost).where(CrawledPost.domain == domain).limit(10)
    result = await db.execute(query)
    posts = result.scalars().all()
    
    if not posts:
        raise HTTPException(status_code=404, detail="No knowledge found for this domain")
    
    knowledge_list = [{"title": p.title, "summary": p.content[:200]} for p in posts]
    
    # 2. 템플릿 매니저를 통해 자동 생성
    manager = TemplateManager()
    template = await manager.generate_template_from_knowledge(domain, knowledge_list)
    
    return {"template": template}
