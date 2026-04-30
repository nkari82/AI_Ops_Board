import asyncio
import re
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
import asyncpraw
import feedparser
from bs4 import BeautifulSoup

from config import settings


class RedditCrawler:
    """
    Reddit 크롤러 - dual mode 지원
    1. API mode: asyncpraw 사용 (rate limit 주의)
    2. RSS mode: Reddit RSS 피드 사용 (rate limit 없음, Approval 불필요)
    """

    def __init__(self):
        self.use_rss = getattr(settings, "REDDIT_USE_RSS", False)
        self.rss_feeds = getattr(
            settings,
            "REDDIT_RSS_FEEDS",
            "https://www.reddit.com/r/LocalLLaMA/.rss,https://www.reddit.com/r/ArtificialIntelligence/.rss",
        )

        self.rss_max_chunks = int(getattr(settings, "REDDIT_RSS_MAX_CONTENT_CHUNKS", 4) or 4)
        self.rss_max_links_per_entry = int(getattr(settings, "REDDIT_RSS_MAX_LINKS_PER_ENTRY", 2) or 2)
        self.rss_fetch_link_content = bool(getattr(settings, "REDDIT_RSS_FETCH_LINK_CONTENT", True))
        self.rss_link_timeout_seconds = int(getattr(settings, "REDDIT_RSS_LINK_TIMEOUT_SECONDS", 6) or 6)
        self.rss_max_link_content_chars = int(getattr(settings, "REDDIT_RSS_MAX_LINK_CONTENT_CHARS", 1200) or 1200)
        self.rss_selftext_max_chars = int(getattr(settings, "REDDIT_RSS_SELFTEXT_MAX_CHARS", 4000) or 4000)
        self.rss_link_min_text_chars = int(getattr(settings, "REDDIT_RSS_LINK_MIN_TEXT_CHARS", 160) or 160)
        self.rss_link_max_noise_ratio = float(getattr(settings, "REDDIT_RSS_LINK_MAX_NOISE_RATIO", 0.45) or 0.45)
        self.rss_link_max_same_line_ratio = float(getattr(settings, "REDDIT_RSS_LINK_MAX_SAME_LINE_RATIO", 0.6) or 0.6)

        # API mode용 Reddit 인스턴스
        self.reddit = None
        if settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET and not self.use_rss:
            self.reddit = asyncpraw.Reddit(
                client_id=settings.REDDIT_CLIENT_ID,
                client_secret=settings.REDDIT_CLIENT_SECRET,
                user_agent=settings.REDDIT_USER_AGENT,
            )

    async def crawl(self, subreddit_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """크롤링 실행 - 모드에 따라 자동 전환"""

        if self.use_rss:
            return await self._crawl_via_rss(limit)
        if self.reddit:
            return await self._crawl_via_api(subreddit_name, limit)
        # 설정 없으면 RSS 폴백
        return await self._crawl_via_rss(limit)

    async def _crawl_via_api(self, subreddit_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """API 모드: asyncpraw 사용"""

        if not self.reddit:
            return await self._crawl_via_rss(limit)

        try:
            subreddit = await self.reddit.subreddit(subreddit_name)
            posts = []

            async for submission in subreddit.hot(limit=limit):
                posts.append(
                    {
                        "title": submission.title,
                        "url": f"https://reddit.com{submission.permalink}",
                        "score": submission.score,
                        "selftext": submission.selftext[:500] if submission.selftext else "",
                        "created_utc": submission.created_utc,
                        "num_comments": submission.num_comments,
                        "source": "reddit_api",
                    }
                )

            return posts
        except Exception:
            # API 실패 시 RSS로 폴백
            return await self._crawl_via_rss(limit)

    async def _crawl_via_rss(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        RSS 모드: Reddit RSS 피드 사용
        - Rate limit 없음
        - Reddit API 승인 불필요
        - 외부 서비스 의존 (reddit.com 서버)
        """

        posts: List[Dict[str, Any]] = []
        feed_urls = [url.strip() for url in self.rss_feeds.split(",") if url.strip()]
        if not feed_urls:
            return posts

        per_feed = max(1, limit // len(feed_urls) + 1)

        timeout = aiohttp.ClientTimeout(total=10)
        headers = {
            "User-Agent": settings.REDDIT_USER_AGENT,
            "Accept": "application/rss+xml, application/atom+xml, text/xml;q=0.9, */*;q=0.8",
        }
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            for feed_url in feed_urls:
                try:
                    async with session.get(feed_url) as resp:
                        if resp.status != 200:
                            continue
                        text = await resp.text()
                        feed_posts = await self._parse_rss(text, per_feed, session)
                        posts.extend(feed_posts)
                except Exception:
                    continue

        # 점수순 정렬 후 limit 적용
        posts.sort(key=lambda x: x.get("score", 0), reverse=True)
        return posts[:limit]

    async def _parse_rss(self, xml_content: str, limit: int, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """feedparser + bs4 기반 RSS/Atom 파싱"""
        parsed = feedparser.parse(xml_content)
        if not getattr(parsed, "entries", None):
            return []

        posts: List[Dict[str, Any]] = []
        for entry in parsed.entries[:limit]:
            item = await self._entry_to_post(entry, session)
            if item:
                posts.append(item)
        return posts

    async def _entry_to_post(self, entry: Any, session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        title = self._clean_text(getattr(entry, "title", ""))
        if not title:
            return None

        url = self._extract_entry_url(entry)
        score = self._safe_int(getattr(entry, "reddit_score", None), default=1)
        num_comments = self._safe_int(getattr(entry, "reddit_num_comments", None), default=0)
        created_utc = self._extract_entry_timestamp(entry)

        primary_html = self._extract_entry_html(entry)
        content_blocks = self._extract_clean_blocks(primary_html)
        links = self._extract_links(primary_html, base_url=url)

        linked_blocks: List[str] = []
        linked_urls: List[str] = []
        rss_quality: Dict[str, Any] = {
            "entryBlocks": len(content_blocks),
            "extractedLinks": 0,
            "acceptedLinks": 0,
            "skippedLinks": [],
        }
        if self.rss_fetch_link_content:
            link_candidates = [link for link in links if self._is_external_article_link(link, post_url=url)]
            rss_quality["extractedLinks"] = len(link_candidates)
            linked_urls = link_candidates[: self.rss_max_links_per_entry]
            linked_blocks, skip_reasons = await self._fetch_link_blocks(linked_urls, session)
            rss_quality["acceptedLinks"] = len(linked_blocks)
            rss_quality["skippedLinks"] = skip_reasons

        selftext = self._compose_selftext(content_blocks, linked_blocks, linked_urls)

        return {
            "title": title,
            "url": url,
            "score": score,
            "selftext": selftext,
            "created_utc": created_utc,
            "num_comments": num_comments,
            "source": "reddit_rss",
            "rss_quality": rss_quality,
        }

    def _extract_entry_url(self, entry: Any) -> str:
        url = self._clean_text(getattr(entry, "link", ""))
        if url:
            return url
        links = getattr(entry, "links", None) or []
        for item in links:
            href = self._clean_text(getattr(item, "href", ""))
            if href:
                return href
        return ""

    def _extract_entry_html(self, entry: Any) -> str:
        # content -> summary -> description 우선순위
        contents = getattr(entry, "content", None) or []
        for c in contents:
            value = getattr(c, "value", "")
            if value:
                return str(value)

        summary = getattr(entry, "summary", "")
        if summary:
            return str(summary)

        description = getattr(entry, "description", "")
        return str(description or "")

    def _extract_entry_timestamp(self, entry: Any) -> int:
        published = self._clean_text(getattr(entry, "published", ""))
        if not published:
            published = self._clean_text(getattr(entry, "updated", ""))
        if not published:
            return 0

        try:
            dt = parsedate_to_datetime(published)
            return int(dt.timestamp())
        except Exception:
            return 0

    def _extract_clean_blocks(self, html: str) -> List[str]:
        if not html:
            return []

        # Reddit RSS sometimes double-escapes markup (e.g. "&lt;div&gt;")
        # Unescape first so BeautifulSoup can parse actual tags.
        decoded_html = unescape(str(html))
        soup = BeautifulSoup(decoded_html, "lxml")
        for tag in soup(["script", "style", "iframe", "noscript"]):
            tag.decompose()

        blocks: List[str] = []
        for node in soup.find_all(["p", "li", "blockquote"]):
            text = self._clean_text(node.get_text(" ", strip=True))
            if text and len(text) >= 20:
                blocks.append(text)

        if not blocks:
            raw = self._clean_text(soup.get_text(" ", strip=True))
            if raw:
                blocks.append(raw)

        deduped: List[str] = []
        seen = set()
        for block in blocks:
            key = block.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(block)
            if len(deduped) >= self.rss_max_chunks:
                break
        return deduped

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        if not html:
            return []
        decoded_html = unescape(str(html))
        soup = BeautifulSoup(decoded_html, "lxml")
        links: List[str] = []
        for anchor in soup.find_all("a", href=True):
            href = self._clean_text(anchor.get("href", ""))
            if not href:
                continue
            absolute = urljoin(base_url or "", href)
            parsed = urlparse(absolute)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                continue
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if normalized not in links:
                links.append(normalized)
        return links

    def _is_external_article_link(self, link: str, post_url: str) -> bool:
        if not link:
            return False
        link_host = urlparse(link).netloc
        post_host = urlparse(post_url or "").netloc
        if not link_host:
            return False
        # reddit 내부 링크는 제외하고 외부 원문만 수집
        if "reddit.com" in link_host:
            return False
        if post_host and link_host == post_host:
            return False
        return True

    async def _fetch_link_blocks(self, urls: List[str], session: aiohttp.ClientSession) -> tuple[List[str], List[Dict[str, str]]]:
        if not urls:
            return [], []

        results = await asyncio.gather(
            *(self._fetch_single_link_text(url, session) for url in urls),
            return_exceptions=True,
        )

        blocks: List[str] = []
        skip_reasons: List[Dict[str, str]] = []
        for idx, value in enumerate(results):
            source_url = urls[idx]
            if isinstance(value, Exception):
                skip_reasons.append({"url": source_url, "reason": "fetch_exception"})
                continue
            if not value:
                skip_reasons.append({"url": source_url, "reason": "empty_content"})
                continue

            quality = self._evaluate_link_text_quality(value)
            if quality["accepted"]:
                blocks.append(value)
            else:
                skip_reasons.append({"url": source_url, "reason": quality["reason"]})

        return blocks, skip_reasons

    async def _fetch_single_link_text(self, url: str, session: aiohttp.ClientSession) -> str:
        timeout = aiohttp.ClientTimeout(total=max(2, self.rss_link_timeout_seconds))
        headers = {
            "User-Agent": settings.REDDIT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        try:
            async with session.get(url, timeout=timeout, headers=headers, allow_redirects=True) as resp:
                if resp.status != 200:
                    return ""
                html = await resp.text(errors="ignore")
        except Exception:
            return ""

        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "iframe", "noscript"]):
            tag.decompose()

        article = soup.find("article") or soup.find("main")
        base_node = article if article is not None else soup.body
        text = ""
        if base_node is not None:
            text = self._clean_text(base_node.get_text(" ", strip=True))
        if not text:
            text = self._clean_text(soup.get_text(" ", strip=True))

        return text[: self.rss_max_link_content_chars]

    def _evaluate_link_text_quality(self, text: str) -> Dict[str, Any]:
        normalized = self._clean_text(text)
        if len(normalized) < self.rss_link_min_text_chars:
            return {"accepted": False, "reason": "too_short"}

        sentences = [chunk.strip() for chunk in re.split(r"[.!?]\s+", normalized) if chunk.strip()]
        if len(sentences) >= 5:
            sentence_counts: Dict[str, int] = {}
            for sentence in sentences:
                key = sentence[:120].lower()
                sentence_counts[key] = sentence_counts.get(key, 0) + 1
            repeated_ratio = max(sentence_counts.values()) / len(sentences)
            if repeated_ratio > self.rss_link_max_same_line_ratio:
                return {"accepted": False, "reason": "repeated_sentences"}

        low = normalized.lower()
        noise_markers = [
            "accept cookies",
            "enable javascript",
            "subscribe now",
            "sign in",
            "log in",
            "advertisement",
            "privacy policy",
            "terms of service",
        ]
        marker_hits = sum(1 for marker in noise_markers if marker in low)
        noise_ratio = marker_hits / max(1, len(noise_markers))
        if noise_ratio > self.rss_link_max_noise_ratio:
            return {"accepted": False, "reason": "noise_heavy"}

        return {"accepted": True, "reason": "accepted"}

    def _compose_selftext(self, content_blocks: List[str], linked_blocks: List[str], linked_urls: List[str]) -> str:
        parts: List[str] = []

        if content_blocks:
            parts.append("[RSS_ENTRY_CONTENT]")
            parts.extend(f"- {block}" for block in content_blocks)

        if linked_blocks:
            parts.append("[LINKED_SOURCE_CONTENT]")
            parts.extend(f"- {block}" for block in linked_blocks)

        if linked_urls:
            parts.append("[EXTRACTED_LINKS]")
            parts.extend(f"- {url}" for url in linked_urls)

        merged = "\n".join(parts).strip()
        return merged[: self.rss_selftext_max_chars]

    def _clean_text(self, value: str) -> str:
        text = unescape(str(value or ""))
        text = " ".join(text.split())
        return text.strip()

    def _safe_int(self, value: Any, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return default

    def _mock_data(self) -> List[Dict[str, Any]]:
        return []
