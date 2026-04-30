from __future__ import annotations

import json
import os
import tempfile
import threading
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import fcntl  # type: ignore
except ImportError:  # pragma: no cover - windows fallback
    fcntl = None  # type: ignore

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from backend.db import get_db
    from backend.db_models import CrawledPost
    from backend.services.recommendation_engine import RecommendationEngine
    from backend.services.recommendation_quality import (
        apply_sparse_data_score_guard,
        cap_combo_boost,
        compute_quality_confidence,
        quality_band_from_confidence,
    )
    from backend.services.recommendation_runtime import (
        build_snapshot_id,
        get_latest_post_updated_at,
        is_cache_fresh,
        load_cached_settings,
        load_snapshot_store,
        upsert_snapshot,
    )
except ModuleNotFoundError:
    from db import get_db
    from db_models import CrawledPost
    from services.recommendation_engine import RecommendationEngine
    from services.recommendation_quality import (
        apply_sparse_data_score_guard,
        cap_combo_boost,
        compute_quality_confidence,
        quality_band_from_confidence,
    )
    from services.recommendation_runtime import (
        build_snapshot_id,
        get_latest_post_updated_at,
        is_cache_fresh,
        load_cached_settings,
        load_snapshot_store,
        upsert_snapshot,
    )

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
recommendation_engine = RecommendationEngine()


def _select_replay_candidate(
    snapshot_id: str,
    snapshot: dict[str, Any],
    settings: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, bool]:
    for item in settings:
        if isinstance(item, dict) and str(item.get("recommendationSnapshotId") or "") == snapshot_id:
            return item, False

    snapshot_domain = str(snapshot.get("domain") or "")
    for item in settings:
        if isinstance(item, dict) and str(item.get("domain") or "") == snapshot_domain:
            return item, True

    return None, True

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
_FEEDBACK_WRITE_LOCK = threading.Lock()


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
        if not isinstance(payload, dict):
            continue

        rating_raw = payload.get("rating")
        try:
            rating = int(rating_raw)
        except (TypeError, ValueError):
            continue
        if rating < 1 or rating > 5:
            continue

        payload["rating"] = rating
        rows.append(payload)
    return rows


def _append_feedback(entry: dict[str, Any]) -> None:
    """Append feedback entry to JSONL file with atomic write protection.
    
    Uses atomic write-then-rename pattern to prevent concurrent write corruption.
    Validates rating before write to prevent data pollution.
    """
    _FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Validate rating before write
    rating = entry.get("rating")
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        raise ValueError(f"Invalid rating: {rating}. Must be integer 1-5.")
    
    tmp_path: Path | None = None
    with _FEEDBACK_WRITE_LOCK:
        try:
            # Read existing content
            existing_content = ""
            if _FEEDBACK_PATH.exists():
                try:
                    existing_content = _FEEDBACK_PATH.read_text(encoding="utf-8")
                except (IOError, OSError):
                    # If read fails, start fresh (better than corrupting)
                    existing_content = ""
            
            # Write to temp file first (atomic operation)
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=_FEEDBACK_PATH.parent,
                delete=False,
                encoding="utf-8",
                suffix=".tmp"
            ) as tmp:
                tmp_path = Path(tmp.name)
                # Write existing content + new entry
                tmp.write(existing_content)
                tmp.write(json.dumps(entry, ensure_ascii=False) + "\n")
                tmp.flush()
                os.fsync(tmp.fileno())  # Force OS-level sync
            
            # Atomic rename (OS-level atomic on most systems)
            tmp_path.replace(_FEEDBACK_PATH)
        except Exception as e:
            # Clean up temp file if it exists
            if tmp_path is not None:
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise RuntimeError(f"Failed to append feedback: {e}") from e


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
            unique_tech = set(_normalize_str_list(getattr(p, "tech_stack", []), limit=20))
            for tech in unique_tech:
                tech_counter[tech] += 1

        top_categories = [name for name, _ in category_counter.most_common(3)]
        top_tech = [name for name, _ in tech_counter.most_common(5)]

        feedback = feedback_by_domain.get(domain, [])
        avg_feedback = 0.0
        if feedback:
            avg_feedback = sum(int(x.get("rating", 0)) for x in feedback) / max(len(feedback), 1)

        selected_models = _DEFAULT_MODEL_ROUTING
        selected_workflow = _DEFAULT_WORKFLOW
        for row in reversed(feedback):
            row_models = _normalize_str_list(row.get("chosen_models"), limit=10)
            row_workflow = _normalize_str_list(row.get("chosen_workflow"), limit=10)
            if row_models:
                selected_models = row_models
            if row_workflow:
                selected_workflow = row_workflow
            if row_models or row_workflow:
                break

        evidence_count = len(domain_posts)
        feedback_count = len(feedback)

        base_score = min(100, 40 + evidence_count * 3)
        feedback_bonus = int((avg_feedback - 3.0) * 8) if feedback else 0
        score = max(0, min(100, base_score + feedback_bonus))

        combo_boost = 0
        if domain in {"게임 클라이언트", "Unity", "Unreal"}:
            if normalized_client_engine:
                if normalized_client_engine == "유니티" and domain == "Unity":
                    combo_boost += 4
                elif normalized_client_engine == "언리얼" and domain == "Unreal":
                    combo_boost += 4
                elif normalized_client_engine == "자체엔진" and domain == "게임 클라이언트":
                    combo_boost += 4

            if normalized_game_genre:
                combo_boost += 2

            if normalized_dev_language:
                combo_boost += 2

        capped_combo_boost = cap_combo_boost(combo_boost, evidence_count)
        score_before_sparse_guard = min(100, score + capped_combo_boost)
        score_after_sparse_guard = apply_sparse_data_score_guard(score_before_sparse_guard, evidence_count)
        sparse_penalty_applied = score_after_sparse_guard < score_before_sparse_guard
        score = score_after_sparse_guard

        quality_confidence = compute_quality_confidence(evidence_count, feedback_count)
        quality_band = quality_band_from_confidence(quality_confidence)

        evidence_highlights = [
            f"{(getattr(post, 'title', '') or '').strip()[:72]} | cat={((getattr(post, 'category', '') or 'N/A').strip() or 'N/A')}"
            for post in domain_posts[:3]
            if isinstance(getattr(post, 'title', None), str) and (getattr(post, 'title', '').strip())
        ]
        if not evidence_highlights:
            evidence_highlights = ["근거 데이터가 부족하여 기본 추천 로직을 사용했습니다."]

        dynamic_subagents, dynamic_views, official_categories = _derive_dynamic_harness_metadata(domain_posts, domain=domain)

        recommendation_snapshot = {
            "computedAt": datetime.now(timezone.utc).isoformat(),
            "domain": domain,
            "inputFilters": {
                "clientEngine": normalized_client_engine,
                "gameGenre": normalized_game_genre,
                "devLanguage": normalized_dev_language,
            },
            "evidenceCount": evidence_count,
            "feedbackCount": feedback_count,
            "topCategories": top_categories[:3],
            "topTech": top_tech[:5],
            "selectedModels": selected_models[:4],
            "selectedWorkflow": selected_workflow[:4],
        }
        snapshot_id = build_snapshot_id(recommendation_snapshot)
        upsert_snapshot(snapshot_id, recommendation_snapshot)

        settings.append(
            {
                "domain": domain,
                "title": f"{domain} 추천 운용 셋팅",
                "score": score,
                "modelRouting": selected_models,
                "workflow": selected_workflow,
                "mcp": top_tech or ["MCP Router", "Knowledge Sync"],
                "rules": top_categories or ["깨알팁", "실전 사례"],
                "reason": (
                    (
                        f"{domain} 도메인 포스트 {evidence_count}건 + 피드백 {feedback_count}건 기반 추천"
                        if domain_posts or feedback
                        else f"{domain} 도메인 데이터 부족으로 기본 추천값 적용"
                    )
                    + (
                        f" | 엔진={normalized_client_engine or '-'}, 장르={normalized_game_genre or '-'}, 언어={normalized_dev_language or '-'}"
                        if domain in {"게임 클라이언트", "Unity", "Unreal"}
                        else ""
                    )
                ),
                "evidenceCount": evidence_count,
                "feedbackCount": feedback_count,
                "qualityConfidence": quality_confidence,
                "qualityBand": quality_band,
                "scoreBreakdown": {
                    "baseScore": base_score,
                    "feedbackBonus": feedback_bonus,
                    "comboBoost": capped_combo_boost,
                    "sparsePenaltyApplied": sparse_penalty_applied,
                    "finalScore": score,
                },
                "evidenceHighlights": evidence_highlights,
                "subagentCandidates": dynamic_subagents,
                "dynamicViews": dynamic_views,
                "officialCategories": official_categories,
                "recommendationSnapshot": recommendation_snapshot,
                "recommendationSnapshotId": snapshot_id,
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


@router.get("/snapshots/{snapshot_id}")
async def get_recommendation_snapshot(snapshot_id: str) -> dict[str, Any]:
    store = load_snapshot_store()
    snapshot = store.get(snapshot_id)
    if not isinstance(snapshot, dict):
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snapshot


@router.post("/replay")
async def replay_recommendation_snapshot(snapshot_id: str = Query(..., min_length=6)) -> dict[str, Any]:
    store = load_snapshot_store()
    snapshot = store.get(snapshot_id)
    if not isinstance(snapshot, dict):
        raise HTTPException(status_code=404, detail="Snapshot not found")

    return {
        "status": "ok",
        "snapshotId": snapshot_id,
        "snapshot": snapshot,
        "replayHint": "Use snapshot.domain and snapshot.inputFilters to request /api/recommendations with identical filters.",
    }


@router.post("/replay/execute")
async def replay_execute_recommendation_snapshot(
    snapshot_id: str = Query(..., min_length=6),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    store = load_snapshot_store()
    snapshot = store.get(snapshot_id)
    if not isinstance(snapshot, dict):
        raise HTTPException(status_code=404, detail="Snapshot not found")

    input_filters = snapshot.get("inputFilters") if isinstance(snapshot.get("inputFilters"), dict) else {}
    client_engine = str(input_filters.get("clientEngine") or "").strip() or None
    game_genre = str(input_filters.get("gameGenre") or "").strip() or None
    dev_language = str(input_filters.get("devLanguage") or "").strip() or None

    settings = await get_recommendations(
        db=db,
        client_engine=client_engine,
        game_genre=game_genre,
        dev_language=dev_language,
    )
    candidate, drifted = _select_replay_candidate(snapshot_id, snapshot, settings)

    if candidate is None:
        raise HTTPException(status_code=404, detail="No replayable recommendation found")

    return {
        "status": "ok",
        "snapshotId": snapshot_id,
        "drifted": drifted,
        "snapshot": snapshot,
        "replayedRecommendation": candidate,
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
