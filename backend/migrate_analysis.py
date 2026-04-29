import asyncio
import sys
from pathlib import Path

from sqlalchemy import Text, func, or_, select

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
for candidate in (CURRENT_DIR, PROJECT_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.append(candidate_str)

try:
    from backend.db import async_session_maker
    from backend.db_models import CrawledPost
    from backend.services.crawled_post_ingest import CrawledPostIngestService
except ModuleNotFoundError:
    from db import async_session_maker
    from db_models import CrawledPost
    from services.crawled_post_ingest import CrawledPostIngestService


def _parse_args() -> tuple[bool, int | None]:
    # ultra-light argv parsing (works both local + in container)
    force = "--force" in sys.argv
    limit: int | None = None
    if "--limit" in sys.argv:
        try:
            idx = sys.argv.index("--limit")
            limit = int(sys.argv[idx + 1])
        except Exception:
            limit = None
    return force, limit


async def migrate_data() -> None:
    force, limit = _parse_args()

    service = CrawledPostIngestService()

    async with async_session_maker() as db:
        query = select(CrawledPost).where(
            or_(
                CrawledPost.doc_type.is_(None),
                CrawledPost.tech_stack.is_(None),
                CrawledPost.summary.is_(None),
                CrawledPost.category.is_(None),
                CrawledPost.tags.is_(None),
                CrawledPost.title_ko.is_(None),
                CrawledPost.summary_ko.is_(None),
                func.length(func.trim(func.coalesce(CrawledPost.summary, ""))) == 0,
                CrawledPost.tech_stack.cast(Text).ilike("%API 오류%"),
                CrawledPost.tech_stack.cast(Text).ilike("%LLM 생성 실패%"),
                func.coalesce(CrawledPost.extra_data["risk"].cast(Text), "").not_in(["low", "medium", "high"]),
            )
        ).order_by(CrawledPost.created_at.desc())
        if limit is not None and limit > 0:
            query = query.limit(limit)

        result = await db.execute(query)
        posts = result.scalars().all()

        targets = posts if force else [post for post in posts if service.needs_reanalysis(post)]

        print(f"Found {len(posts)} candidate posts to inspect.")
        print(f"Reanalyzing {len(targets)} posts. (force={force}, limit={limit})")

        updated_count = 0
        failed_count = 0

        for post in targets:
            print(f"Analyzing: {post.id} - {post.title}")
            try:
                await service.reanalyze_post(db, post)
                await db.commit()
                updated_count += 1
                print(f"Updated: {post.id} - {post.title}")
            except Exception as exc:
                await db.rollback()
                failed_count += 1
                print(f"Error updating {post.id} - {post.title}: {exc}")

        print(
            f"Migration complete. updated={updated_count}, failed={failed_count}, total={len(targets)}"
        )


if __name__ == "__main__":
    # Usage:
    # - default: reanalyze only polluted rows
    # - force: reanalyze all candidates regardless of current fields
    #   docker compose exec backend python migrate_analysis.py --force --limit 50
    asyncio.run(migrate_data())
