from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from backend.db import get_db
    from backend.db_models import CrawledPost
    from backend.services.recommendation_engine import RecommendationEngine
except ModuleNotFoundError:
    from db import get_db
    from db_models import CrawledPost
    from services.recommendation_engine import RecommendationEngine

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
recommendation_engine = RecommendationEngine()

_ALLOWED_DOMAINS = [
    "게임 클라이언트",
    "게임 서버",
    "프론트엔드",
    "백엔드",
    "Unity",
    "Unreal",
    "로컬 LLM",
    "Agent/MCP",
    "기타",
]

_DEFAULT_MODEL_ROUTING = ["Gemini Flash", "Pollinations mistral", "Groq fallback"]
_DEFAULT_WORKFLOW = ["수집 → 분류 → 요약", "카드 검수", "템플릿 생성"]

_FEEDBACK_PATH = Path(__file__).resolve().parents[1] / "data" / "recommendation_feedback.jsonl"


class RecommendationFeedbackRequest(BaseModel):
    domain: str
    rating: int = Field(ge=1, le=5)
    note: str = ""
    chosen_models: list[str] = Field(default_factory=list)
    chosen_workflow: list[str] = Field(default_factory=list)


def _normalize_str_list(value: Any, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if not text or text in result:
            continue
        result.append(text)
        if len(result) >= limit:
            break
    return result


def _load_feedback() -> list[dict[str, Any]]:
    if not _FEEDBACK_PATH.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in _FEEDBACK_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _append_feedback(entry: dict[str, Any]) -> None:
    _FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _FEEDBACK_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


@router.get("")
async def get_recommendations(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    result = await db.execute(select(CrawledPost).order_by(CrawledPost.updated_at.desc()).limit(600))
    posts = result.scalars().all()
    if not posts:
        return await recommendation_engine.build_settings(db, limit=600)

    by_domain: dict[str, list[Any]] = defaultdict(list)
    for post in posts:
        domain = (post.domain or "기타").strip() if isinstance(post.domain, str) else "기타"
        if domain not in _ALLOWED_DOMAINS:
            domain = "기타"
        by_domain[domain].append(post)

    feedback_rows = _load_feedback()
    feedback_by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in feedback_rows:
        domain = row.get("domain")
        if isinstance(domain, str):
            feedback_by_domain[domain].append(row)

    settings: list[dict[str, Any]] = []
    for domain in _ALLOWED_DOMAINS:
        domain_posts = by_domain.get(domain, [])
        category_counter = Counter(
            p.category.strip() for p in domain_posts if isinstance(p.category, str) and p.category.strip()
        )
        tech_counter = Counter()
        for p in domain_posts:
            for tech in _normalize_str_list(getattr(p, "tech_stack", []), limit=20):
                tech_counter[tech] += 1

        top_categories = [name for name, _ in category_counter.most_common(3)]
        top_tech = [name for name, _ in tech_counter.most_common(5)]

        feedback = feedback_by_domain.get(domain, [])
        avg_feedback = 0.0
        if feedback:
            avg_feedback = sum(int(x.get("rating", 0)) for x in feedback) / max(len(feedback), 1)

        base_score = min(100, 40 + len(domain_posts) * 3)
        feedback_bonus = int((avg_feedback - 3.0) * 8) if feedback else 0
        score = max(0, min(100, base_score + feedback_bonus))

        settings.append(
            {
                "domain": domain,
                "title": f"{domain} 추천 운용 셋팅",
                "score": score,
                "modelRouting": _DEFAULT_MODEL_ROUTING,
                "workflow": _DEFAULT_WORKFLOW,
                "mcp": top_tech or ["MCP Router", "Knowledge Sync"],
                "rules": top_categories or ["깨알팁", "실전 사례"],
                "reason": (
                    f"{domain} 도메인 포스트 {len(domain_posts)}건 + 피드백 {len(feedback)}건 기반 추천"
                    if domain_posts or feedback
                    else f"{domain} 도메인 데이터 부족으로 기본 추천값 적용"
                ),
                "evidenceCount": len(domain_posts),
                "feedbackCount": len(feedback),
            }
        )

    return settings


@router.post("/feedback")
async def submit_recommendation_feedback(payload: RecommendationFeedbackRequest) -> dict[str, Any]:
    if payload.domain not in _ALLOWED_DOMAINS:
        raise HTTPException(status_code=400, detail="Unsupported domain")

    entry = {
        "domain": payload.domain,
        "rating": payload.rating,
        "note": payload.note.strip(),
        "chosen_models": payload.chosen_models,
        "chosen_workflow": payload.chosen_workflow,
    }
    _append_feedback(entry)
    return {"status": "ok"}
