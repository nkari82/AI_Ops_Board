from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db
from services.knowledge_manager import KnowledgeManager
from services.template_manager import TemplateManager

router = APIRouter(prefix="", tags=["knowledge", "templates"])

knowledge_manager = KnowledgeManager()
template_manager = TemplateManager()

@router.get("/knowledge")
async def get_knowledge_cards(db: AsyncSession = Depends(get_db)):
    return await knowledge_manager.generate_knowledge_cards(db)

@router.get("/templates/{tech_stack}")
async def get_template(tech_stack: str):
    return await template_manager.generate_template(tech_stack)
