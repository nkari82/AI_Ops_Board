from __future__ import annotations

from typing import Any

from sqlalchemy import Text, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db_models import CrawledPost


class DataQualityMonitor:
    async def get_quality_metrics(self, db: AsyncSession) -> dict[str, Any]:
        total = await db.scalar(select(func.count()).select_from(CrawledPost)) or 0

        polluted_query = select(func.count()).select_from(CrawledPost).where(
            or_(
                CrawledPost.doc_type.is_(None),
                CrawledPost.tech_stack.is_(None),
                CrawledPost.summary.is_(None),
                CrawledPost.category.is_(None),
                CrawledPost.tags.is_(None),
                func.length(func.trim(func.coalesce(CrawledPost.summary, ""))) == 0,
                CrawledPost.tech_stack.cast(Text).ilike("%API 오류%"),
                CrawledPost.tech_stack.cast(Text).ilike("%LLM 생성 실패%"),
            )
        )
        polluted = await db.scalar(polluted_query) or 0

        domain_rows = await db.execute(
            select(CrawledPost.domain, func.count().label("count"))
            .group_by(CrawledPost.domain)
            .order_by(func.count().desc())
        )
        category_rows = await db.execute(
            select(CrawledPost.category, func.count().label("count"))
            .group_by(CrawledPost.category)
            .order_by(func.count().desc())
        )

        return {
            "totalPosts": int(total),
            "pollutedPosts": int(polluted),
            "qualityScore": 0 if total == 0 else round((1 - (polluted / total)) * 100, 2),
            "domains": [
                {"domain": row[0] or "(none)", "count": int(row[1])}
                for row in domain_rows.all()
            ],
            "categories": [
                {"category": row[0] or "(none)", "count": int(row[1])}
                for row in category_rows.all()
            ],
        }
