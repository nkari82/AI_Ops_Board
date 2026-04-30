from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from importlib import import_module

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from backend.config import settings
except ModuleNotFoundError:
    from config import settings

try:
    from backend.services.llm_router import LLMRouter
    from backend.services.recommendation_baselines import get_domain_baseline, merge_unique
    from backend.services.recommendation_quality import (
        apply_sparse_data_score_guard,
        compute_quality_confidence,
        quality_band_from_confidence,
    )
    from backend.services.recommendation_runtime import (
        build_snapshot_id,
        get_latest_post_updated_at,
        load_cached_settings,
        save_cached_settings,
        upsert_snapshot,
    )
except ModuleNotFoundError:
    from services.llm_router import LLMRouter
    from services.recommendation_baselines import get_domain_baseline, merge_unique
    from services.recommendation_quality import (
        apply_sparse_data_score_guard,
        compute_quality_confidence,
        quality_band_from_confidence,
    )
    from services.recommendation_runtime import (
        build_snapshot_id,
        get_latest_post_updated_at,
        load_cached_settings,
        save_cached_settings,
        upsert_snapshot,
    )

try:
    CrawledPost = import_module("backend.db_models").CrawledPost
except ModuleNotFoundError:
    CrawledPost = import_module("db_models").CrawledPost

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

_FEEDBACK_PATH = Path(__file__).resolve().parents[1] / "data" / "recommendation_feedback.jsonl"


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


class RecommendationEngine:
    def __init__(self) -> None:
        self.llm_router = LLMRouter()

    def _has_any_llm_key(self) -> bool:
        # Avoid expensive failover attempts when running keyless harness.
        candidates = [
            getattr(settings, "GOOGLE_AI_STUDIO_KEY", None),
            getattr(settings, "GROQ_API_KEY", None),
            getattr(settings, "OPENROUTER_API_KEY", None),
            getattr(settings, "MISTRAL_API_KEY", None),
            getattr(settings, "DEEPSEEK_API_KEY", None),
            getattr(settings, "CEREBRAS_API_KEY", None),
            getattr(settings, "SAMBANOVA_API_KEY", None),
            getattr(settings, "HUGGINGFACE_TOKEN", None),
            getattr(settings, "POLLINATIONS_API_KEY", None),
            getattr(settings, "OPENAI_API_KEY", None),
            getattr(settings, "ANTHROPIC_API_KEY", None),
        ]
        return any(isinstance(v, str) and v.strip() for v in candidates)

    def _load_feedback_by_domain(self) -> dict[str, list[dict[str, Any]]]:
        if not _FEEDBACK_PATH.exists():
            return {}
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

        by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            domain = row.get("domain")
            if isinstance(domain, str) and domain.strip():
                by_domain[domain.strip()].append(row)
        return dict(by_domain)

    def _compute_signature(
        self,
        *,
        domain: str,
        baseline_version: int,
        evidence_count: int,
        evidence_latest_updated_at: str | None,
        top_tech: list[str],
        top_categories: list[str],
        feedback_count: int,
        avg_feedback: float,
    ) -> str:
        payload = {
            "domain": domain,
            "baselineVersion": baseline_version,
            "evidenceCount": evidence_count,
            "evidenceLatestUpdatedAt": evidence_latest_updated_at,
            "topTech": top_tech,
            "topCategories": top_categories,
            "feedbackCount": feedback_count,
            "avgFeedback": round(avg_feedback, 4),
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def build_settings(self, db: AsyncSession, limit: int = 500) -> list[dict[str, Any]]:
        result = await db.execute(select(CrawledPost).order_by(CrawledPost.updated_at.desc()).limit(limit))
        posts = result.scalars().all()

        feedback_by_domain = self._load_feedback_by_domain()

        settings: list[dict[str, Any]] = []
        for domain in _ALLOWED_DOMAINS:
            domain_posts = [post for post in posts if (post.domain or "기타") == domain]

            tech_counts: dict[str, int] = {}
            category_counts: dict[str, int] = {}
            evidence_latest = None
            for post in domain_posts:
                updated_at = getattr(post, "updated_at", None)
                if updated_at and (evidence_latest is None or updated_at > evidence_latest):
                    evidence_latest = updated_at

                for tech in (post.tech_stack or []):
                    if isinstance(tech, str) and tech.strip():
                        tech_counts[tech.strip()] = tech_counts.get(tech.strip(), 0) + 1
                if isinstance(post.category, str) and post.category.strip():
                    category = post.category.strip()
                    category_counts[category] = category_counts.get(category, 0) + 1

            top_tech = [k for k, _ in sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
            top_categories = [k for k, _ in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3]]

            feedback_rows = feedback_by_domain.get(domain, [])
            feedback_count = len(feedback_rows)
            avg_feedback = 0.0
            if feedback_rows:
                avg_feedback = sum(int(x.get("rating", 0)) for x in feedback_rows) / max(len(feedback_rows), 1)

            evidence_count = len(domain_posts)
            feedback_count = len(feedback_rows)

            base_score = min(100, 40 + evidence_count * 3)
            feedback_bonus = int((avg_feedback - 3.0) * 8) if feedback_rows else 0
            score = max(0, min(100, base_score + feedback_bonus))
            score_before_sparse_guard = score
            score = apply_sparse_data_score_guard(score, evidence_count)
            sparse_penalty_applied = score < score_before_sparse_guard

            quality_confidence = compute_quality_confidence(evidence_count, feedback_count)
            quality_band = quality_band_from_confidence(quality_confidence)

            evidence_highlights = [
                f"{(getattr(post, 'title', '') or '').strip()[:72]} | cat={((getattr(post, 'category', '') or 'N/A').strip() or 'N/A')}"
                for post in domain_posts[:3]
                if isinstance(getattr(post, 'title', None), str) and (getattr(post, 'title', '').strip())
            ]
            if not evidence_highlights:
                evidence_highlights = ["근거 데이터가 부족하여 기본 추천 로직을 사용했습니다."]

            baseline = get_domain_baseline(domain)
            baseline_version = int(baseline.get("baselineVersion") or 1)

            merged_rules = merge_unique(top_categories, list(baseline.get("rules") or []), limit=4)
            merged_mcp = merge_unique(top_tech, list(baseline.get("mcp") or []), limit=6)

            evidence_latest_iso = None
            if evidence_latest is not None:
                try:
                    evidence_latest_iso = evidence_latest.isoformat()
                except Exception:
                    evidence_latest_iso = str(evidence_latest)

            signature = self._compute_signature(
                domain=domain,
                baseline_version=baseline_version,
                evidence_count=evidence_count,
                evidence_latest_updated_at=evidence_latest_iso,
                top_tech=top_tech,
                top_categories=top_categories,
                feedback_count=feedback_count,
                avg_feedback=avg_feedback,
            )

            dynamic_subagents, dynamic_views, official_categories = _derive_dynamic_harness_metadata(domain_posts, domain=domain)

            recommendation_snapshot = {
                "computedAt": datetime.now(timezone.utc).isoformat(),
                "domain": domain,
                "inputFilters": {
                    "clientEngine": "",
                    "gameGenre": "",
                    "devLanguage": "",
                },
                "evidenceCount": evidence_count,
                "feedbackCount": feedback_count,
                "topCategories": top_categories[:3],
                "topTech": top_tech[:5],
                "selectedModels": list(baseline.get("modelRouting") or [])[:4],
                "selectedWorkflow": list(baseline.get("workflow") or [])[:4],
            }
            snapshot_id = build_snapshot_id(recommendation_snapshot)
            upsert_snapshot(snapshot_id, recommendation_snapshot)

            settings.append(
                {
                    "domain": domain,
                    "title": f"{domain} 추천 운용 셋팅",
                    "score": score,
                    "modelRouting": list(baseline.get("modelRouting") or []),
                    "workflow": list(baseline.get("workflow") or []),
                    "mcp": merged_mcp,
                    "rules": merged_rules,
                    "reason": (
                        f"{domain} 도메인 포스트 {evidence_count}건 + 피드백 {feedback_count}건 기반 추천"
                        if domain_posts or feedback_rows
                        else f"{domain} 데이터 부족으로 기본 추천 사용"
                    ),
                    "evidenceCount": evidence_count,
                    "feedbackCount": feedback_count,
                    "qualityConfidence": quality_confidence,
                    "qualityBand": quality_band,
                    "scoreBreakdown": {
                        "baseScore": base_score,
                        "feedbackBonus": feedback_bonus,
                        "comboBoost": 0,
                        "sparsePenaltyApplied": sparse_penalty_applied,
                        "finalScore": score,
                    },
                    "evidenceHighlights": evidence_highlights,
                    "evidenceLatestUpdatedAt": evidence_latest_iso,
                    "signature": signature,
                    "subagentCandidates": dynamic_subagents,
                    "dynamicViews": dynamic_views,
                    "officialCategories": official_categories,
                    "recommendationSnapshot": recommendation_snapshot,
                    "recommendationSnapshotId": snapshot_id,
                }
            )

        return settings

    async def rebuild_cache_with_llm(
        self,
        db: AsyncSession,
        *,
        trigger: str,
        limit: int = 600,
        max_refine_domains: int | None = None,
    ) -> list[dict[str, Any]]:
        base_settings = await self.build_settings(db, limit=limit)

        cache_payload = load_cached_settings() or {}
        cached_settings = cache_payload.get("settings") if isinstance(cache_payload, dict) else None
        cached_by_domain: dict[str, dict[str, Any]] = {}
        if isinstance(cached_settings, list):
            for row in cached_settings:
                if isinstance(row, dict) and isinstance(row.get("domain"), str):
                    cached_by_domain[row["domain"]] = row

        # Keep previously refined settings when the evidence signature is unchanged.
        merged_settings: list[dict[str, Any]] = []
        to_refine: list[dict[str, Any]] = []
        for item in base_settings:
            domain = str(item.get("domain") or "")
            signature = str(item.get("signature") or "")
            cached = cached_by_domain.get(domain)
            cached_sig = str(cached.get("signature") or "") if isinstance(cached, dict) else ""

            if cached and signature and cached_sig and cached_sig == signature:
                merged_settings.append(cached)
            else:
                merged_settings.append(item)
                to_refine.append(item)

        marker_before_save = await get_latest_post_updated_at(db)

        # Keyless harness: skip LLM refinement to avoid expensive provider failover.
        if not to_refine or not self._has_any_llm_key():
            latest_marker = await get_latest_post_updated_at(db)
            if latest_marker == marker_before_save:
                save_cached_settings(settings=merged_settings, generated_by=trigger, latest_post_updated_at=latest_marker)
            return merged_settings

        if max_refine_domains is not None:
            max_refine_domains = max(0, int(max_refine_domains))

        # Prioritize by evidence volume.
        to_refine_sorted = sorted(
            to_refine,
            key=lambda x: int(x.get("evidenceCount") or 0),
            reverse=True,
        )

        if max_refine_domains is not None:
            to_refine_sorted = to_refine_sorted[:max_refine_domains]

        refined_domains = {str(x.get("domain") or ""): x for x in to_refine_sorted}

        refined_settings: list[dict[str, Any]] = []
        for item in merged_settings:
            domain = str(item.get("domain") or "")
            if domain in refined_domains:
                refined = await self._refine_domain_setting_with_llm(item)
                refined_settings.append(refined)
            else:
                refined_settings.append(item)

        # Re-check marker AFTER refinement to detect if posts arrived during LLM processing.
        # If marker changed, skip cache save to avoid storing stale data.
        # This also prevents stale signatures (computed at line 241) from being cached.
        latest_marker = await get_latest_post_updated_at(db)
        if latest_marker == marker_before_save:
            save_cached_settings(settings=refined_settings, generated_by=trigger, latest_post_updated_at=latest_marker)
        return refined_settings

    async def _refine_domain_setting_with_llm(self, setting: dict[str, Any]) -> dict[str, Any]:
        domain = str(setting.get("domain") or "기타")
        prompt = f"""당신은 하네스 운영 추천 최적화 엔진입니다.
아래 입력을 기반으로 운영 추천을 JSON으로만 반환하세요.

입력:
{json.dumps(setting, ensure_ascii=False)}

출력 JSON 스키마:
{{
  "modelRouting": ["...", "...", "..."],
  "workflow": ["...", "...", "..."],
  "rules": ["...", "...", "..."],
  "reason": "한글 1~2문장"
}}

규칙:
- modelRouting/workflow/rules는 각각 최대 4개
- 하네스 운영 재사용성을 우선
- 비용 절감: 무료/저비용/구독형 조합을 균형 있게 유지
- domain={domain}
JSON 외 텍스트 금지
"""
        try:
            raw = await self.llm_router.generate(
                prompt=prompt,
                provider="gemini",
                max_tokens=320,
                temperature=0.0,
            )
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                obj = json.loads(raw[start : end + 1])
                if isinstance(obj, dict):
                    model_routing = obj.get("modelRouting")
                    workflow = obj.get("workflow")
                    rules = obj.get("rules")
                    reason = obj.get("reason")

                    if isinstance(model_routing, list) and model_routing:
                        setting["modelRouting"] = [str(x).strip() for x in model_routing if str(x).strip()][:4]
                    if isinstance(workflow, list) and workflow:
                        setting["workflow"] = [str(x).strip() for x in workflow if str(x).strip()][:4]
                    if isinstance(rules, list) and rules:
                        setting["rules"] = [str(x).strip() for x in rules if str(x).strip()][:4]
                    if isinstance(reason, str) and reason.strip():
                        setting["reason"] = reason.strip()
        except Exception:
            return setting
        return setting
