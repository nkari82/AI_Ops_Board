from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db_models import CrawledPost
from models import Domain
from services.analyzer import ContentAnalyzer


@dataclass
class NormalizedCrawlItem:
    title: str
    url: str
    source: str
    source_type: str
    content: str = ""
    score: Optional[int] = None
    domain_hint: Optional[str] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)


class CrawledPostIngestService:
    def __init__(self):
        self.analyzer = ContentAnalyzer()

    async def ingest_items(
        self,
        db: AsyncSession,
        raw_items: List[Dict[str, Any]],
        *,
        source_name: Literal["github", "hn", "youtube", "reddit"],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[CrawledPost]:
        posts: List[CrawledPost] = []
        for raw in raw_items:
            normalized = self.normalize_item(source_name, raw, context=context)
            if not normalized:
                continue
            post = await self.ingest_item(db, normalized)
            if post is None:
                continue
            posts.append(post)
        return posts

    async def ingest_item(self, db: AsyncSession, item: NormalizedCrawlItem) -> Optional[CrawledPost]:
        if not self._is_classifiable(item):
            return None
        analysis = await self.build_analysis_fields(item)
        sanitized = self.sanitize_analysis_fields(analysis, item)
        return await self.upsert_post(db, item, sanitized)

    def normalize_item(
        self,
        source_name: str,
        raw: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[NormalizedCrawlItem]:
        context = context or {}
        if source_name == "github":
            return NormalizedCrawlItem(
                title=raw.get("name", "").strip(),
                url=raw.get("html_url", "").strip(),
                source="github:trending",
                source_type="github",
                content=(raw.get("description") or "").strip(),
                score=raw.get("stargazers_count"),
                domain_hint=self.detect_domain(raw.get("description") or raw.get("name") or ""),
                extra_data={
                    "language": raw.get("language"),
                    "topics": raw.get("topics") or [],
                },
            )
        if source_name == "hn":
            return NormalizedCrawlItem(
                title=raw.get("title", "").strip(),
                url=raw.get("link", "").strip(),
                source="hackernews:top",
                source_type="hn",
                content="",
                score=raw.get("score"),
                domain_hint=self.detect_domain(raw.get("title") or ""),
                extra_data={
                    "by": raw.get("by"),
                    "comments_count": raw.get("comments_count"),
                    "time": raw.get("time"),
                },
            )
        if source_name == "youtube":
            url = raw.get("url", "").strip()
            return NormalizedCrawlItem(
                title=raw.get("title", "").strip(),
                url=url,
                source=f"youtube:{context.get('url', url)}",
                source_type="youtube",
                content=(raw.get("content") or "").strip(),
                score=raw.get("score"),
                domain_hint=self.detect_domain((raw.get("content") or raw.get("title") or "")),
                extra_data={},
            )
        if source_name == "reddit":
            source_marker = raw.get("source") or "reddit"
            subreddit = context.get("subreddit") or "unknown"
            return NormalizedCrawlItem(
                title=raw.get("title", "").strip(),
                url=raw.get("url", "").strip(),
                source=f"{source_marker}:{subreddit}",
                source_type="reddit",
                content=(raw.get("selftext") or "").strip(),
                score=raw.get("score"),
                domain_hint=self.detect_domain((raw.get("selftext") or raw.get("title") or "")),
                extra_data={
                    "created_utc": raw.get("created_utc"),
                    "num_comments": raw.get("num_comments"),
                    "source_mode": source_marker,
                    "rss_quality": raw.get("rss_quality") if isinstance(raw.get("rss_quality"), dict) else None,
                },
            )
        return None

    async def build_analysis_fields(self, item: NormalizedCrawlItem) -> Dict[str, Any]:
        analysis_text = (item.content or item.title or "").strip()
        domain = self._normalize_domain(item.domain_hint)
        return await self.analyzer.analyze(analysis_text, item.url, domain, title=item.title)

    def sanitize_analysis_fields(self, analysis: Dict[str, Any], item: NormalizedCrawlItem) -> Dict[str, Any]:
        summary = (analysis.get("summary_ko") or analysis.get("summary") or "").strip()
        if not summary:
            summary = self._fallback_summary(item)

        title_ko = (analysis.get("title_ko") or "").strip() or None

        category = (analysis.get("category") or "깨알팁").strip()
        if category not in {"실전 운용", "아키텍처", "실전 사례", "깨알팁", "주의/함정", "플러그인/MCP"}:
            category = "깨알팁"
        doc_type = (analysis.get("type") or "Knowledge Article").strip()
        tech_stack = self._sanitize_list(analysis.get("tech_stack"), limit=3, max_len=40)
        tags = self._sanitize_list(analysis.get("tags"), limit=5, max_len=30)
        risk = analysis.get("risk") if analysis.get("risk") in {"low", "medium", "high"} else None
        domain = analysis.get("domain") or item.domain_hint or Domain.기타.value

        return {
            "title_ko": title_ko,
            "summary": summary,       # legacy: 한글 요약
            "summary_ko": summary,    # 명시적으로도 저장
            "category": category,
            "doc_type": doc_type,
            "tech_stack": tech_stack,
            "tags": tags,
            "risk": risk,
            "domain": domain,
        }

    async def upsert_post(self, db: AsyncSession, item: NormalizedCrawlItem, analysis: Dict[str, Any]) -> CrawledPost:
        existing = await db.scalar(select(CrawledPost).where(CrawledPost.url == item.url))

        merged_extra_data: Dict[str, Any] = {}
        if existing and isinstance(existing.extra_data, dict):
            merged_extra_data.update(existing.extra_data)
        merged_extra_data.update({k: v for k, v in item.extra_data.items() if v is not None})
        if analysis.get("risk"):
            merged_extra_data["risk"] = analysis["risk"]

        merged_values = {
            "updated_at": func.now(),
            "title": item.title or (existing.title if existing else ""),
            "title_ko": (analysis.get("title_ko") if "title_ko" in analysis else (existing.title_ko if existing else None)),
            "url": item.url,
            "source": item.source or (existing.source if existing else ""),
            "source_type": item.source_type or (existing.source_type if existing else "unknown"),
            "content": (item.content or (existing.content if existing else "") or "").strip(),
            "score": item.score if item.score is not None else (existing.score if existing else 0),
            "extra_data": merged_extra_data,
            "summary": analysis.get("summary") or (existing.summary if existing else self._fallback_summary(item)),
            "summary_ko": (analysis.get("summary_ko") if "summary_ko" in analysis else (existing.summary_ko if existing else None)),
            "domain": analysis.get("domain") or item.domain_hint or (existing.domain if existing else Domain.기타.value),
            "category": (analysis.get("category") if analysis.get("category") in {"실전 운용", "아키텍처", "실전 사례", "깨알팁", "주의/함정", "플러그인/MCP"} else None)
            or (existing.category if existing else "깨알팁"),
            "doc_type": analysis.get("doc_type") or (existing.doc_type if existing else "Knowledge Article"),
            "tech_stack": analysis["tech_stack"] if "tech_stack" in analysis else (existing.tech_stack if existing and isinstance(existing.tech_stack, list) else []),
            "tags": analysis["tags"] if "tags" in analysis else (existing.tags if existing and isinstance(existing.tags, list) else []),
        }

        stmt = insert(CrawledPost).values(**merged_values)
        stmt = stmt.on_conflict_do_update(
            constraint="uix_crawled_post_url",
            set_=merged_values,
        ).returning(CrawledPost.id)
        row_id = await db.scalar(stmt)
        await db.flush()
        post = await db.scalar(select(CrawledPost).where(CrawledPost.id == row_id))
        return post

    async def reanalyze_post(self, db: AsyncSession, post: CrawledPost) -> CrawledPost:
        item = NormalizedCrawlItem(
            title=post.title,
            url=post.url,
            source=post.source,
            source_type=post.source_type,
            content=post.content or "",
            score=post.score,
            domain_hint=post.domain,
            extra_data=post.extra_data if isinstance(post.extra_data, dict) else {},
        )
        analysis = await self.build_analysis_fields(item)
        sanitized = self.sanitize_analysis_fields(analysis, item)
        return await self.upsert_post(db, item, sanitized)

    def needs_reanalysis(self, post: CrawledPost) -> bool:
        if not post.doc_type or not post.summary or not post.category:
            return True
        if not isinstance(post.tech_stack, list) or self._looks_invalid_list(post.tech_stack):
            return True
        if not isinstance(post.tags, list):
            return True
        risk = post.extra_data.get("risk") if isinstance(post.extra_data, dict) else None
        return risk not in {"low", "medium", "high"}

    def _is_classifiable(self, item: NormalizedCrawlItem) -> bool:
        """LLM 분류가 신뢰 불가능할 정도로 짧은 데이터는 저장하지 않는다."""
        title = (item.title or "").strip()
        content = (item.content or "").strip()
        combined = f"{title}\n{content}".strip()

        # 문자 기준: 한글/영문/숫자만 카운트
        signal_len = len("".join(ch for ch in combined if ch.isalnum() or ('가' <= ch <= '힣')))

        def _to_positive_int(raw: Any, default_value: int) -> int:
            try:
                return max(1, int(raw or default_value))
            except Exception:
                return default_value

        min_content_len = _to_positive_int(getattr(settings, "MIN_CLASSIFIABLE_CONTENT_LEN", "120"), 120)
        min_signal_len = _to_positive_int(getattr(settings, "MIN_CLASSIFIABLE_SIGNAL_LEN", "160"), 160)

        # 분류 최소 조건
        # - 본문이 충분히 길거나
        # - 제목+본문 신호 길이가 충분해야 함
        return len(content) >= min_content_len or signal_len >= min_signal_len

    def detect_domain(self, text: str) -> str:
        normalized = (text or "").lower()
        if "unity" in normalized:
            return "Unity"
        if "unreal" in normalized:
            return "Unreal"
        if "react" in normalized or "frontend" in normalized or "next.js" in normalized or "nextjs" in normalized:
            return "프론트엔드"
        # NOTE: keep keyword-based fallback until LLM-domain classifier is fully relied on
        if "python" in normalized or "backend" in normalized or "fastapi" in normalized:
            return "백엔드"
        if "llm" in normalized or "agent" in normalized or "mcp" in normalized:
            return "Agent/MCP"
        return "기타"

    def _fallback_summary(self, item: NormalizedCrawlItem) -> str:
        base = (item.content or item.title or "").strip()
        if not base:
            return "요약할 원문이 없습니다."
        return base[:200]

    def _sanitize_list(self, values: Any, *, limit: int, max_len: int) -> List[str]:
        if isinstance(values, str):
            raw_items = [part.strip() for part in values.split(",")]
        elif isinstance(values, list):
            raw_items = [str(part).strip() for part in values]
        else:
            raw_items = []

        cleaned: List[str] = []
        for item in raw_items:
            if not item or item in cleaned:
                continue
            lowered = item.lower()
            if any(marker in lowered for marker in ["api 오류", "llm 생성 실패", "token", "unauthorized", "forbidden"]):
                continue
            if len(item) > max_len or any(sep in item for sep in ["\n", ": ", "http://", "https://"]):
                continue
            cleaned.append(item)
        return cleaned[:limit]

    def _looks_invalid_list(self, values: List[str]) -> bool:
        for value in values:
            normalized = str(value).strip().lower()
            if not normalized:
                continue
            if any(marker in normalized for marker in ["api 오류", "llm 생성 실패", "token", "unauthorized", "forbidden"]):
                return True
            if len(normalized) > 40 or "http://" in normalized or "https://" in normalized or "\n" in normalized:
                return True
        return False

    def _normalize_domain(self, value: Optional[str]) -> Domain:
        if value and value in {item.value for item in Domain}:
            return Domain(value)
        return Domain.기타
