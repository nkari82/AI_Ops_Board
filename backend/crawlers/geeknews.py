from __future__ import annotations

from typing import Any, Dict, List

import feedparser
from bs4 import BeautifulSoup

from config import settings


class GeekNewsCrawler:
    def __init__(self) -> None:
        self.rss_url = (getattr(settings, "GEEKNEWS_RSS_URL", "") or "https://news.hada.io/rss/news").strip()

    def _clean_html(self, html: str) -> str:
        if not html:
            return ""
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(" ", strip=True)
        return " ".join(text.split())

    async def crawl_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        parsed = feedparser.parse(self.rss_url)
        entries = getattr(parsed, "entries", []) or []

        results: List[Dict[str, Any]] = []
        for entry in entries[: max(1, limit)]:
            raw_content = ""
            if getattr(entry, "content", None):
                first = entry.content[0]
                raw_content = getattr(first, "value", "") or ""
            elif getattr(entry, "summary", None):
                raw_content = entry.summary or ""

            cleaned = self._clean_html(raw_content)

            tags = []
            for t in getattr(entry, "tags", []) or []:
                term = (getattr(t, "term", "") or "").strip()
                if term:
                    tags.append(term)

            results.append(
                {
                    "title": (getattr(entry, "title", "") or "").strip(),
                    "link": (getattr(entry, "link", "") or "").strip(),
                    "summary": cleaned,
                    "author": (getattr(entry, "author", "") or "").strip(),
                    "published": (getattr(entry, "published", "") or "").strip(),
                    "tags": tags,
                    "source": "geeknews:rss",
                }
            )

        return [item for item in results if item.get("title") and item.get("link")]
