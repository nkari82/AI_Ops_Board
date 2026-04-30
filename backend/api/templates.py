import io
import zipfile
from importlib import import_module
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _load_runtime_dependencies() -> tuple[Any, Any, Any]:
    try:
        db_module = import_module("backend.db")
        models_module = import_module("backend.db_models")
        template_module = import_module("backend.services.template_manager")
    except ModuleNotFoundError:
        db_module = import_module("db")
        models_module = import_module("db_models")
        template_module = import_module("services.template_manager")

    return db_module.get_db, models_module.CrawledPost, template_module.TemplateManager


get_db, CrawledPost, TemplateManager = _load_runtime_dependencies()

router = APIRouter(prefix="/ops-templates", tags=["templates"])


@router.get("/clone-instructions")
async def get_clone_instructions(domain: str) -> dict[str, str]:
    manager = TemplateManager()
    script = manager.build_clone_script(domain)
    return {
        "domain": domain,
        "script": script,
        "hint": "스크립트를 clone.sh로 저장 후 실행하면 템플릿 저장소 골격이 생성됩니다.",
    }

@router.post("/generate-zip")
async def generate_template_zip(
    domain: str,
    payload: dict[str, Any] | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
) -> Response:
    # 1. 지식 데이터 로드
    query = select(CrawledPost).where(CrawledPost.domain == domain).limit(100)
    result = await db.execute(query)
    posts = result.scalars().all()
    
    knowledge_list = [
        {
            "title": p.title,
            "summary": (p.summary or p.content or p.title or ""),
        }
        for p in posts
    ]

    # 데이터가 없어도 도메인 기본 번들을 생성해 404 대신 fallback ZIP을 제공
    if not knowledge_list:
        knowledge_list = [{"title": domain, "summary": "도메인 기본 운영 템플릿"}]

    recommendation = payload or {}

    # 2. 템플릿 번들 생성 (추천셋팅 반영)
    manager = TemplateManager()
    try:
        bundle = await manager.generate_template_bundle(domain, knowledge_list, recommendation)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # 3. Zip 생성
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for filename, content in bundle.items():
            zip_file.writestr(filename, content)
    
    _ = zip_buffer.seek(0)
    
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={domain}-ops-template.zip"}
    )
