from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db import get_db
from db_models import CrawledPost
from services.template_manager import TemplateManager

router = APIRouter(prefix="/templates", tags=["templates"])

from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import io
import zipfile
from db import get_db
from db_models import CrawledPost
from services.template_manager import TemplateManager

router = APIRouter(prefix="/templates", tags=["templates"])

@router.post("/generate-zip")
async def generate_template_zip(domain: str, db: AsyncSession = Depends(get_db)):
    # 1. 지식 데이터 로드
    query = select(CrawledPost).where(CrawledPost.domain == domain).limit(10)
    result = await db.execute(query)
    posts = result.scalars().all()
    
    if not posts:
        raise HTTPException(status_code=404, detail="No knowledge found")
    
    knowledge_list = [{"title": p.title, "summary": p.content[:200]} for p in posts]
    
    # 2. 템플릿 생성
    manager = TemplateManager()
    template_content = await manager.generate_template_from_knowledge(domain, knowledge_list)
    
    # 3. Zip 생성
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("unified-ops.md", template_content)
        zip_file.writestr("AGENTS.md", "# Agent Definitions\n\nGenerated from context.")
        zip_file.writestr("Rule.md", "# Project Rules\n\nGenerated from context.")
    
    zip_buffer.seek(0)
    
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={domain}-ops-template.zip"}
    )
