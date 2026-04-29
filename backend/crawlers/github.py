from github import Github
from typing import List, Dict, Any
from config import settings
import asyncio


class GithubCrawler:
    def __init__(self):
        self.github = None
        if settings.GITHUB_TOKEN:
            self.github = Github(settings.GITHUB_TOKEN)
    
    async def crawl_trending(self, limit: int = 10) -> List[Dict[str, Any]]:
        if not self.github:
            return []
        
        try:
            loop = asyncio.get_event_loop()
            repos = await loop.run_in_executor(
                None,
                self._fetch_trending,
                limit
            )
            return repos
        except Exception as e:
            return []
    
    def _fetch_trending(self, limit: int) -> List[Dict[str, Any]]:
        keywords = ["LLM performance", "Harness CI/CD", "LLM token optimization", "AI agent framework"]
        query = f"({' OR '.join(keywords)}) stars:>500"
        repos = self.github.search_repositories(query=query, sort="stars", order="desc")
        
        results = []
        for repo in repos[:limit]:
            results.append({
                "name": repo.full_name,
                "html_url": repo.html_url,
                "description": repo.description or "",
                "stargazers_count": repo.stargazers_count,
                "language": repo.language,
                "topics": repo.get_topics()
            })
        
        return results
