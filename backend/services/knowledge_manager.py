import json
from typing import Dict, List, Any
from services.llm_router import LLMRouter
from db import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db_models import CrawledPost

class KnowledgeManager:
    def __init__(self):
        self.llm_router = LLMRouter()

    async def generate_knowledge_cards(self, db: AsyncSession) -> List[Dict[str, Any]]:
        query = select(CrawledPost).order_by(CrawledPost.created_at.desc()).limit(10)
        result = await db.execute(query)
        posts = result.scalars().all()
        
        contents = "\n".join([f"- {p.title}: {p.summary}" for p in posts])
        
        prompt = f"""다음은 최근 크롤링된 기술 운영 데이터들입니다. 
이 내용을 요약하여 '오픈코드'와 '클로드코드' 운영에 관한 핵심 인사이트 카드(title, content, category) 5개를 생성하세요.
반드시 JSON 배열 형식으로만 출력하세요.

데이터:
{contents}
"""
        try:
            raw_cards = await self.llm_router.generate(prompt, provider="groq")
            # JSON 배열 추출
            start = raw_cards.find("[")
            end = raw_cards.rfind("]") + 1
            return json.loads(raw_cards[start:end])
        except Exception as e:
            return [{"title": "지식 생성 실패", "content": str(e), "category": "Error"}]
