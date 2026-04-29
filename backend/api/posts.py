from datetime import datetime
from importlib import import_module
from typing import TYPE_CHECKING, Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from backend.db_models import CrawledPost as CrawledPostModel
    from backend.models import BoardCategory, Domain, OperationPost, SourceKind


def _load_runtime_dependencies() -> tuple[Any, Any, Any, Any, Any, Any]:
    try:
        db_module = import_module("backend.db")
        db_models_module = import_module("backend.db_models")
        models_module = import_module("backend.models")
    except ModuleNotFoundError:
        db_module = import_module("db")
        db_models_module = import_module("db_models")
        models_module = import_module("models")
    return (
        db_module.get_db,
        db_models_module.CrawledPost,
        models_module.OperationPost,
        models_module.Domain,
        models_module.BoardCategory,
        models_module.SourceKind,
    )


get_db, CrawledPost, OperationPost, Domain, BoardCategory, SourceKind = _load_runtime_dependencies()
get_db = cast(Any, get_db)
CrawledPost = cast(Any, CrawledPost)
OperationPost = cast(Any, OperationPost)
Domain = cast(Any, Domain)
BoardCategory = cast(Any, BoardCategory)
SourceKind = cast(Any, SourceKind)

router = APIRouter(prefix="/operation-posts", tags=["posts"])


def _as_optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _as_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item.strip()]
    return []


def _normalize_domain(value: str | None) -> Any:
    if value and value in {item.value for item in Domain}:
        return Domain(value)
    return Domain.기타


def _normalize_category(value: str | None) -> Any:
    if value and value in {item.value for item in BoardCategory}:
        return BoardCategory(value)
    # Avoid biasing everything to '실전 운용' when classification fails
    return BoardCategory.깨알팁


def _extract_risk(post: Any) -> str | None:
    extra_data = getattr(post, "extra_data", None)
    if isinstance(extra_data, dict):
        risk = extra_data.get("risk")
        if risk in {"low", "medium", "high"}:
            return risk
    return None


def _extract_sources(post: Any) -> list[str]:
    sources: list[str] = []
    for value in [_as_optional_str(getattr(post, "url", None)), _as_optional_str(getattr(post, "source", None))]:
        if value and value not in sources:
            sources.append(value)
    return sources


def _map_operation_post(post: Any) -> Any:
    content = _as_optional_str(getattr(post, "content", None)) or ""
    title = _as_optional_str(getattr(post, "title", None)) or "Untitled"
    summary = _as_optional_str(getattr(post, "summary", None)) or (content[:200] if content else title)
    updated_at = getattr(post, "updated_at", None) or getattr(post, "created_at", None) or datetime.now()
    url = _as_optional_str(getattr(post, "url", None))

    return OperationPost(
        id=int(getattr(post, "id", 0)),
        title=title,
        title_ko=_as_optional_str(getattr(post, "title_ko", None)),
        summary=summary,
        summary_ko=_as_optional_str(getattr(post, "summary_ko", None)) or summary,
        content=content,
        category=_normalize_category(_as_optional_str(getattr(post, "category", None))),
        doc_type=_as_optional_str(getattr(post, "doc_type", None)),
        tech_stack=_as_string_list(getattr(post, "tech_stack", None)),
        domain=_normalize_domain(_as_optional_str(getattr(post, "domain", None))),
        score=int(getattr(post, "score", 0) or 0),
        source_kind=SourceKind.crawled,
        sources=_extract_sources(post),
        updated_at=updated_at,
        action="원문 보기" if url else None,
        tags=_as_string_list(getattr(post, "tags", None)),
        risk=_extract_risk(post),
    )


@router.get("", response_model=list[OperationPost])
async def get_operation_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
) -> list[Any]:
    result = await db.execute(select(CrawledPost).order_by(CrawledPost.created_at.desc()).offset(skip).limit(limit))
    posts = result.scalars().all()

    return [_map_operation_post(post) for post in posts]


@router.get("/{post_id}", response_model=OperationPost)
async def get_operation_post(
    post_id: int,
    db: AsyncSession = Depends(get_db)
) -> Any:
    result = await db.execute(select(CrawledPost).where(CrawledPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return _map_operation_post(post)
