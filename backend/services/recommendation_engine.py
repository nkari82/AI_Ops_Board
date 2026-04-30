from __future__ import annotations

from typing import Any
from importlib import import_module

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


class RecommendationEngine:
    async def build_settings(self, db: AsyncSession, limit: int = 500) -> list[dict[str, Any]]:
        result = await db.execute(
            select(CrawledPost).order_by(CrawledPost.updated_at.desc()).limit(limit)
        )
        posts = result.scalars().all()

        settings: list[dict[str, Any]] = []
        for domain in _ALLOWED_DOMAINS:
            domain_posts = [post for post in posts if (post.domain or "기타") == domain]
            score = min(100, 40 + len(domain_posts) * 8)

            tech_counts: dict[str, int] = {}
            category_counts: dict[str, int] = {}
            for post in domain_posts:
                for tech in (post.tech_stack or []):
                    if isinstance(tech, str) and tech.strip():
                        tech_counts[tech] = tech_counts.get(tech, 0) + 1
                if isinstance(post.category, str) and post.category.strip():
                    category_counts[post.category] = category_counts.get(post.category, 0) + 1

            top_tech = [k for k, _ in sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)[:3]]
            top_categories = [k for k, _ in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:2]]

            settings.append(
                {
                    "domain": domain,
                    "title": f"{domain} 추천 운용 셋팅",
                    "score": score,
                    "modelRouting": ["Gemini Flash", "Pollinations mistral", "Groq fallback"],
                    "workflow": ["수집 → 분류 → 요약", "카드 검수", "템플릿 생성"],
                    "mcp": top_tech if top_tech else ["MCP Router", "Knowledge Sync"],
                    "rules": top_categories if top_categories else ["깨알팁", "실전 사례"],
                    "reason": (
                        f"{domain} 도메인 포스트 {len(domain_posts)}건 기반 추천"
                        if domain_posts
                        else f"{domain} 데이터 부족으로 기본 추천 사용"
                    ),
                }
            )

        return settings
