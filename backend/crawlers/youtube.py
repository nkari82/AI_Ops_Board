from __future__ import annotations

import logging
import re

from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger(__name__)


class YoutubeCrawler:
    def get_video_id(self, url: str) -> str | None:
        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
        return match.group(1) if match else None

    def _preferred_languages(self) -> list[str]:
        # Ordered fallback list for caption lookup
        return ["ko", "en", "en-US", "en-GB", "ja"]

    async def crawl(self, url: str) -> dict[str, str] | None:
        video_id = self.get_video_id(url)
        if not video_id:
            logger.warning("YouTube crawl skipped: invalid video URL: %s", url)
            return None

        try:
            api = YouTubeTranscriptApi()
            transcript = api.fetch(video_id, languages=self._preferred_languages())
            full_text = " ".join(getattr(entry, "text", str(entry)) for entry in transcript).strip()
            if not full_text:
                logger.warning("YouTube crawl skipped: empty transcript for %s", video_id)
                return None

            return {
                "url": url,
                "title": f"YouTube Video: {video_id}",
                "content": full_text,
            }
        except Exception as exc:
            logger.error("Transcript extraction failed for %s: %s", video_id, exc)
            return None
