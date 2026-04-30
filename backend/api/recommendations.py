from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from backend.db import get_db
    from backend.db_models import CrawledPost
    from backend.services.recommendation_engine import RecommendationEngine
    from backend.services.recommendation_runtime import get_latest_post_updated_at, is_cache_fresh, load_cached_settings
except ModuleNotFoundError:
    from db import get_db
    from db_models import CrawledPost
    from services.recommendation_engine import RecommendationEngine
    from services.recommendation_runtime import get_latest_post_updated_at, is_cache_fresh, load_cached_settings

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

_DEFAULT_MODEL_ROUTING = [
    "Gemini Flash",
    "Pollinations mistral",
    "Codex CLI (subscription)",
    "Groq fallback",
]
_DEFAULT_WORKFLOW = ["수집 → 분류 → 요약", "카드 검수", "템플릿 생성"]

_FEEDBACK_PATH = Path(__file__).resolve().parents[1] / "data" / "recommendation_feedback.jsonl"
_FEEDBACK_SCHEMA_VERSION = 1
_MAX_NOTE_LEN = 500


def _derive_dynamic_harness_metadata(domain_posts: list[Any], *, domain: str) -> tuple[list[str], list[str], dict[str, list[str]]]:
    text_parts: list[str] = []
    for post in domain_posts[:80]:
        for value in [getattr(post, "title", ""), getattr(post, "summary", ""), getattr(post, "content", "")]:
            if isinstance(value, str) and value.strip():
                text_parts.append(value.strip()[:500])
    lowered = "\n".join(text_parts).lower()

    subagents: list[str] = ["Planner", "Implementer", "Reviewer"]
    keyword_subagents: list[tuple[str, list[str]]] = [
        ("Debugger", ["debug", "trace", "에러", "bug", "exception"]),
        ("Security Reviewer", ["security", "취약", "auth", "permission", "xss", "csrf"]),
        ("Performance Tuner", ["latency", "throughput", "성능", "optimiz", "profil"]),
        ("Data/RAG Specialist", ["rag", "embedding", "vector", "retrieval", "index"]),
        ("Release Operator", ["deploy", "release", "rollout", "on-call", "incident"]),
    ]
    for name, keywords in keyword_subagents:
        if any(k in lowered for k in keywords) and name not in subagents:
            subagents.append(name)

    dynamic_views: list[str] = []
    if domain in {"Agent/MCP", "로컬 LLM"}:
        dynamic_views.extend(["providerConfig", "commandsRegistry", "toolsRegistry"])
    if any(k in lowered for k in ["permission", "권한", "sandbox"]):
        dynamic_views.extend(["permissionsMatrix", "sandboxConfig"])
    if any(k in lowered for k in ["hook", "webhook", "event"]):
        dynamic_views.append("hooksConfig")
    if any(k in lowered for k in ["memory", "context", "compaction"]):
        dynamic_views.extend(["autoMemory", "compactionConfig"])

    unique_views: list[str] = []
    for v in dynamic_views:
        if v not in unique_views:
            unique_views.append(v)

    official_opencode = [
        "commands",
        "instructions",
        "agents",
        "providers",
        "mcpServers",
        "lsp",
        "shell",
        "autoCompact",
        "theme",
        "debug",
    ]
    official_claude = [
        "skills",
        "memory",
        "tools",
        "mcp",
        "subagents",
        "rules",
        "commands",
        "permissions",
        "model",
        "hooks",
        "output-styles",
    ]

    if any(k in lowered for k in ["oauth", "auth", "token"]):
        if "mcpAuth" not in official_opencode:
            official_opencode.append("mcpAuth")
        if "auth" not in official_claude:
            official_claude.append("auth")

    official_categories = {
        "opencode": official_opencode,
        "claudecode": official_claude,
    }

    return subagents[:8], unique_views[:10], official_categories


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
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _append_feedback(entry: dict[str, Any]) -> None:
    _FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _FEEDBACK_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


@router.get("")
async def get_recommendations(
    db: AsyncSession = Depends(get_db),
    client_engine: str | None = Query(default=None),
    game_genre: str | None = Query(default=None),
    dev_language: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    normalized_client_engine = (client_engine or "").strip()
    normalized_game_genre = (game_genre or "").strip()
    normalized_dev_language = (dev_language or "").strip()

    use_cached = not (normalized_client_engine or normalized_game_genre or normalized_dev_language)
    if use_cached:
        latest_marker = await get_latest_post_updated_at(db)
        cache_payload = load_cached_settings()
        if is_cache_fresh(cache_payload, latest_marker):
            cached_settings = cache_payload.get("settings") if isinstance(cache_payload, dict) else None
            if isinstance(cached_settings, list) and cached_settings:
                return cached_settings

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

        if domain in {"게임 클라이언트", "Unity", "Unreal"}:
            if normalized_client_engine:
                if normalized_client_engine == "유니티" and domain == "Unity":
                    score = min(100, score + 4)
                elif normalized_client_engine == "언리얼" and domain == "Unreal":
                    score = min(100, score + 4)
                elif normalized_client_engine == "자체엔진" and domain == "게임 클라이언트":
                    score = min(100, score + 4)

            if normalized_game_genre:
                score = min(100, score + 2)

            if normalized_dev_language:
                score = min(100, score + 2)

        dynamic_subagents, dynamic_views, official_categories = _derive_dynamic_harness_metadata(domain_posts, domain=domain)

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
                    (
                        f"{domain} 도메인 포스트 {len(domain_posts)}건 + 피드백 {len(feedback)}건 기반 추천"
                        if domain_posts or feedback
                        else f"{domain} 도메인 데이터 부족으로 기본 추천값 적용"
                    )
                    + (
                        f" | 엔진={normalized_client_engine or '-'}, 장르={normalized_game_genre or '-'}, 언어={normalized_dev_language or '-'}"
                        if domain in {"게임 클라이언트", "Unity", "Unreal"}
                        else ""
                    )
                ),
                "evidenceCount": len(domain_posts),
                "feedbackCount": len(feedback),
                "subagentCandidates": dynamic_subagents,
                "dynamicViews": dynamic_views,
                "officialCategories": official_categories,
            }
        )

    return settings


@router.post("/refresh")
async def refresh_recommendations(
    trigger: str = Query(default="manual"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    settings = await recommendation_engine.rebuild_cache_with_llm(db, trigger=trigger, limit=600)
    return {
        "status": "ok",
        "trigger": trigger,
        "count": len(settings),
    }


@router.post("/feedback")
async def submit_recommendation_feedback(payload: RecommendationFeedbackRequest) -> dict[str, Any]:
    if payload.domain not in _ALLOWED_DOMAINS:
        raise HTTPException(status_code=400, detail="Unsupported domain")

    entry = {
        "schema_version": _FEEDBACK_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "domain": payload.domain,
        "rating": payload.rating,
        "note": payload.note.strip()[:_MAX_NOTE_LEN],
        "chosen_models": _normalize_str_list(payload.chosen_models, limit=10),
        "chosen_workflow": _normalize_str_list(payload.chosen_workflow, limit=10),
    }
    _append_feedback(entry)
    return {"status": "ok"}
