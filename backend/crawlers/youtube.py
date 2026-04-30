from __future__ import annotations

import asyncio
import json
import logging
import re
from urllib.parse import quote_plus

import aiohttp
from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger(__name__)


class YoutubeCrawler:
    SEARCH_BASE_URL = "https://www.youtube.com/results?search_query={query}"

    def get_video_id(self, url: str) -> str | None:
        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
        return match.group(1) if match else None

    def _preferred_languages(self) -> list[str]:
        return ["ko", "en", "en-US", "en-GB", "ja"]

    async def crawl(self, url: str) -> dict[str, str] | None:
        video_id = self.get_video_id(url)
        if not video_id:
            logger.warning("YouTube crawl skipped: invalid video URL: %s", url)
            return None

        content = self._fetch_transcript(video_id)
        if not content:
            return None

        return {
            "url": url,
            "title": f"YouTube Video: {video_id}",
            "content": content,
        }

    async def crawl_search(self, query: str, max_videos: int = 8, pages: int = 2) -> list[dict[str, str]]:
        normalized_query = (query or "").strip()
        if not normalized_query:
            logger.warning("YouTube search crawl skipped: empty query")
            return []

        max_pages = max(1, min(int(pages or 1), 5))
        max_items = max(1, min(int(max_videos or 1), 30))

        discovered: list[tuple[str, str]] = []
        seen_ids: set[str] = set()

        for page_index in range(max_pages):
            page_query = normalized_query if page_index == 0 else f"{normalized_query} {page_index + 1}"
            html = await self._fetch_search_page(page_query)
            if not html:
                continue

            page_candidates = self._extract_video_candidates(html)
            for video_id, title in page_candidates:
                if video_id in seen_ids:
                    continue
                seen_ids.add(video_id)
                discovered.append((video_id, title))
                if len(discovered) >= max_items:
                    break

            if len(discovered) >= max_items:
                break

        if not discovered:
            logger.warning("YouTube search crawl: no videos discovered query=%s", normalized_query)
            return []

        tasks = [self._crawl_video_from_id(video_id, title) for video_id, title in discovered[:max_items]]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        items: list[dict[str, str]] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("YouTube search crawl item failed: %s", result)
                continue
            if result:
                items.append(result)

        logger.info(
            "YouTube search crawl finished query=%s pages=%s requested=%s collected=%s",
            normalized_query,
            max_pages,
            max_items,
            len(items),
        )
        return items

    async def _fetch_search_page(self, query: str) -> str:
        url = self.SEARCH_BASE_URL.format(query=quote_plus(query))
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        timeout = aiohttp.ClientTimeout(total=20)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        logger.warning("YouTube search page request failed status=%s query=%s", resp.status, query)
                        return ""
                    return await resp.text()
        except Exception as exc:
            logger.warning("YouTube search page request error query=%s error=%s", query, exc)
            return ""

    def _extract_video_candidates(self, html: str) -> list[tuple[str, str]]:
        text = (html or "").strip()
        if not text:
            return []

        # Primary: ytInitialData JSON extraction
        candidates = self._extract_from_initial_data(text)
        if candidates:
            return candidates

        # Fallback: /watch?v=... pattern
        seen: set[str] = set()
        fallback: list[tuple[str, str]] = []
        for match in re.finditer(r"\/watch\?v=([0-9A-Za-z_-]{11})", text):
            video_id = match.group(1)
            if video_id in seen:
                continue
            seen.add(video_id)
            fallback.append((video_id, f"YouTube Video: {video_id}"))
            if len(fallback) >= 30:
                break
        return fallback

    def _extract_from_initial_data(self, html: str) -> list[tuple[str, str]]:
        marker = "var ytInitialData ="
        start = html.find(marker)
        if start == -1:
            return []

        start = html.find("{", start)
        if start == -1:
            return []

        end_marker = ";</script>"
        end = html.find(end_marker, start)
        if end == -1:
            return []

        blob = html[start:end].strip()
        if not blob:
            return []

        try:
            data = json.loads(blob)
        except Exception:
            return []

        videos: list[tuple[str, str]] = []
        seen: set[str] = set()
        self._walk_video_renderers(data, videos, seen)
        return videos

    def _walk_video_renderers(self, node: object, out: list[tuple[str, str]], seen: set[str]) -> None:
        if isinstance(node, dict):
            if "videoRenderer" in node and isinstance(node["videoRenderer"], dict):
                vr = node["videoRenderer"]
                video_id = vr.get("videoId")
                title = self._extract_renderer_title(vr)
                if isinstance(video_id, str) and len(video_id) == 11 and video_id not in seen:
                    seen.add(video_id)
                    out.append((video_id, title or f"YouTube Video: {video_id}"))
                    if len(out) >= 30:
                        return

            for value in node.values():
                if len(out) >= 30:
                    return
                self._walk_video_renderers(value, out, seen)
            return

        if isinstance(node, list):
            for item in node:
                if len(out) >= 30:
                    return
                self._walk_video_renderers(item, out, seen)

    def _extract_renderer_title(self, vr: dict) -> str:
        title_node = vr.get("title")
        if not isinstance(title_node, dict):
            return ""

        runs = title_node.get("runs")
        if isinstance(runs, list):
            chunks = [str(run.get("text", "")).strip() for run in runs if isinstance(run, dict)]
            return " ".join(chunk for chunk in chunks if chunk).strip()

        simple_text = title_node.get("simpleText")
        return str(simple_text).strip() if simple_text else ""

    async def _crawl_video_from_id(self, video_id: str, title: str) -> dict[str, str] | None:
        content = await asyncio.to_thread(self._fetch_transcript, video_id)
        if not content:
            return None

        return {
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "title": title or f"YouTube Video: {video_id}",
            "content": content,
        }

    def _fetch_transcript(self, video_id: str) -> str:
        try:
            api = YouTubeTranscriptApi()
            transcript = api.fetch(video_id, languages=self._preferred_languages())
            full_text = " ".join(getattr(entry, "text", str(entry)) for entry in transcript).strip()
            if not full_text:
                logger.warning("YouTube crawl skipped: empty transcript for %s", video_id)
                return ""
            return full_text
        except Exception as exc:
            logger.warning("Transcript extraction failed for %s: %s", video_id, exc)
            return ""
