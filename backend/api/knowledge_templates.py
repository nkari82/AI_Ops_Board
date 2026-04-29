from importlib import import_module
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession


def _load_runtime_dependencies() -> tuple[Any, Any, Any]:
    try:
        db_module = import_module("backend.db")
        knowledge_module = import_module("backend.services.knowledge_manager")
        template_module = import_module("backend.services.template_manager")
    except ModuleNotFoundError:
        db_module = import_module("db")
        knowledge_module = import_module("services.knowledge_manager")
        template_module = import_module("services.template_manager")

    return db_module.get_db, knowledge_module.KnowledgeManager, template_module.TemplateManager


get_db, KnowledgeManager, TemplateManager = _load_runtime_dependencies()

router = APIRouter(prefix="", tags=["knowledge", "templates"])

knowledge_manager = KnowledgeManager()
template_manager = TemplateManager()

@router.get("/knowledge")
async def get_knowledge_cards(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    return await knowledge_manager.generate_knowledge_cards(db)

@router.get("/templates/{tech_stack}")
async def get_template(tech_stack: str) -> str:
    try:
        return await template_manager.generate_template(tech_stack)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
