import asyncpraw
import aiohttp
from typing import List, Dict, Any, Optional
from config import settings


class RedditCrawler:
    """
    Reddit 크롤러 - dual mode 지원
    1. API mode: asyncpraw 사용 (rate limit 주의)
    2. RSS mode: Reddit RSS 피드 사용 (rate limit 없음,Approval 불필요)
    """
    
    def __init__(self):
        self.use_rss = getattr(settings, 'REDDIT_USE_RSS', False)
        self.rss_feeds = getattr(settings, 'REDDIT_RSS_FEEDS', 
            'https://www.reddit.com/r/LocalLLaMA/.rss,https://www.reddit.com/r/ArtificialIntelligence/.rss')
        
        # API mode용 Reddit 인스턴스
        self.reddit = None
        if settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET and not self.use_rss:
            self.reddit = asyncpraw.Reddit(
                client_id=settings.REDDIT_CLIENT_ID,
                client_secret=settings.REDDIT_CLIENT_SECRET,
                user_agent=settings.REDDIT_USER_AGENT
            )
    
    async def crawl(self, subreddit_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """크롤링 실행 - 모드에 따라 자동 전환"""
        
        if self.use_rss:
            return await self._crawl_via_rss(limit)
        elif self.reddit:
            return await self._crawl_via_api(subreddit_name, limit)
        else:
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
                posts.append({
                    "title": submission.title,
                    "url": f"https://reddit.com{submission.permalink}",
                    "score": submission.score,
                    "selftext": submission.selftext[:500] if submission.selftext else "",
                    "created_utc": submission.created_utc,
                    "num_comments": submission.num_comments,
                    "source": "reddit_api"
                })
            
            return posts
        except Exception as e:
            # API 실패 시 RSS로 폴백
            return await self._crawl_via_rss(limit)
    
    async def _crawl_via_rss(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        RSS 모드: Reddit RSS 피드 사용
        - Rate limit 없음
        - Reddit API 승인 불필요
        - 외부 서비스 의존 (reddit.com 서버)
        """
        
        posts = []
        feed_urls = [url.strip() for url in self.rss_feeds.split(',') if url.strip()]
        
        async with aiohttp.ClientSession() as session:
            for feed_url in feed_urls:
                try:
                    async with session.get(feed_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            feed_posts = self._parse_rss(text, limit // len(feed_urls) + 1)
                            posts.extend(feed_posts)
                except Exception:
                    continue
        
        # 점수순 정렬 후 limit 적용
        posts.sort(key=lambda x: x.get('score', 0), reverse=True)
        return posts[:limit]
    
    def _parse_rss(self, xml_content: str, limit: int) -> List[Dict[str, Any]]:
        """RSS XML 파싱"""
        import re
        
        posts = []
        
        # entry 패턴 매칭
        entry_pattern = r'<entry>(.*?)</entry>'
        entries = re.findall(entry_pattern, xml_content, re.DOTALL)
        
        for entry in entries[:limit]:
            # 제목 추출
            title_match = re.search(r'<title[^>]*>(.*?)</title>', entry, re.DOTALL)
            title = title_match.group(1) if title_match else ""
            
            # 링크 추출 (Reddit URL)
            link_match = re.search(r'<link[^>]*href=["\'](.*?)["\']', entry, re.DOTALL)
            url = link_match.group(1) if link_match else ""
            
            # Reddit 게시물 ID 추출
            reddit_id_match = re.search(r'reddit\.com/r/\w+/comments/([a-zA-Z0-9]+)', url)
            reddit_id = reddit_id_match.group(1) if reddit_id_match else ""
            
            # 점수 (Reddit에서는 RSS에 직접 없으므로 기본값)
            score_match = re.search(r'<reddit:score>(.*?)</reddit:score>', entry, re.DOTALL)
            score = int(score_match.group(1)) if score_match else 1
            
            # 댓글 수
            comments_match = re.search(r'<reddit:num_comments>(.*?)</reddit:num_comments>', entry, re.DOTALL)
            num_comments = int(comments_match.group(1)) if comments_match else 0
            
            # 작성일
            published_match = re.search(r'<published>(.*?)</published>', entry, re.DOTALL)
            created_utc = 0
            if published_match:
                from email.utils import parsedate_to_datetime
                try:
                    dt = parsedate_to_datetime(published_match.group(1))
                    created_utc = int(dt.timestamp())
                except Exception:
                    pass
            
            # 요약 (content 또는 summary)
            summary_match = re.search(r'<summary[^>]*>(.*?)</summary>', entry, re.DOTALL)
            if not summary_match:
                summary_match = re.search(r'<content[^>]*>(.*?)</content>', entry, re.DOTALL)
            selftext = summary_match.group(1)[:500] if summary_match else ""
            # HTML 태그 제거
            selftext = re.sub(r'<[^>]+>', '', selftext)
            
            if title:
                posts.append({
                    "title": title,
                    "url": url,
                    "score": score,
                    "selftext": selftext,
                    "created_utc": created_utc,
                    "num_comments": num_comments,
                    "source": "reddit_rss"
                })
        
        return posts
    
    def _mock_data(self) -> List[Dict[str, Any]]:
        return []