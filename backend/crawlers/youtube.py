from youtube_transcript_api import YouTubeTranscriptApi
import re

class YoutubeCrawler:
    def get_video_id(self, url: str):
        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
        return match.group(1) if match else None

    async def crawl(self, url: str):
        video_id = self.get_video_id(url)
        if not video_id:
            return None
        
        try:
            transcript = YouTubeTranscriptApi().fetch(video_id, languages=['ko', 'en'])
            # FetchedTranscript is an iterable, we can iterate over it to get snippets
            # Each snippet is an object with 'text', 'start', 'duration'
            # Based on the error, the snippets might not be dictionaries.
            # Let's try accessing the text attribute.
            full_text = " ".join([getattr(entry, 'text', str(entry)) for entry in transcript])
            return {
                "url": url,
                "title": f"YouTube Video: {video_id}",
                "content": full_text
            }
        except Exception as e:
            print(f"Transcript extraction failed: {e}")
            return None
