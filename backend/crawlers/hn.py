import aiohttp
from typing import List, Dict, Any


class HackerNewsCrawler:
    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    
    async def crawl_top_stories(self, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.BASE_URL}/topstories.json") as resp:
                    story_ids = await resp.json()
                
                stories = []
                keywords = ["LLM", "Harness", "AI", "Performance", "Optimization", "Agent"]
                for story_id in story_ids:
                    if len(stories) >= limit:
                        break
                    async with session.get(f"{self.BASE_URL}/item/{story_id}.json") as resp:
                        story = await resp.json()
                        if story and "title" in story:
                            title = story["title"]
                            if any(k.lower() in title.lower() for k in keywords):
                                stories.append({
                                    "title": title,
                                    "link": story.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                                    "score": story.get("score", 0),
                                    "comments_count": story.get("descendants", 0),
                                    "by": story.get("by", ""),
                                    "time": story.get("time", 0)
                                })
                
                return stories
        except Exception as e:
            return []
    
    def _mock_data(self) -> List[Dict[str, Any]]:
        return []
