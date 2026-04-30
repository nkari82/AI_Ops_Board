import json
from importlib import import_module
from typing import Any

from config import settings

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


def _load_runtime_dependencies() -> tuple[Any, Any]:
    try:
        llm_module = import_module("backend.services.llm_router")
        models_module = import_module("backend.db_models")
    except ModuleNotFoundError:
        llm_module = import_module("services.llm_router")
        models_module = import_module("db_models")
    return llm_module.LLMRouter, models_module.CrawledPost


LLMRouter, CrawledPost = _load_runtime_dependencies()

def _default_text_provider() -> str:
    # Prefer cheapest/available first
    if settings.GOOGLE_AI_STUDIO_KEY:
        return "gemini"
    if settings.POLLINATIONS_API_KEY:
        return "pollinations"
    if settings.GROQ_API_KEY:
        return "groq"
    if settings.OPENROUTER_API_KEY:
        return "openrouter"
    if settings.MISTRAL_API_KEY:
        return "mistral"
    if settings.DEEPSEEK_API_KEY:
        return "deepseek"
    if settings.CEREBRAS_API_KEY:
        return "cerebras"
    if settings.SAMBANOVA_API_KEY:
        return "sambanova"
    if settings.HUGGINGFACE_TOKEN:
        return "huggingface"
    return "pollinations"


class KnowledgeManager:
    def __init__(self):
        self.llm_router: Any = LLMRouter()

    async def generate_knowledge_cards(
        self,
        db: AsyncSession,
        new_post: Any | None = None,
    ) -> list[dict[str, Any]]:
        self.llm_router = LLMRouter()
        if new_post:
            posts = [new_post]
        else:
            query = select(CrawledPost).order_by(CrawledPost.created_at.desc()).limit(10)
            result = await db.execute(query)
            posts = result.scalars().all()
        
        contents = "\n".join([f"- {p.title}: {p.summary}" for p in posts])
        
        prompt = f"""다음은 최근 크롤링된 기술 운영 데이터들입니다. 
이 내용을 요약하여 '오픈코드'와 '클로드코드' 운영에 관한 핵심 인사이트 카드 5개를 생성하세요.
각 카드는 다음 필드를 포함해야 합니다:
- title: 제목
- content: 내용
- category: 카테고리 (예: 아키텍처, 실전 사례, 깨알팁)
- type: 문서 타입 (예: Knowledge Article, Troubleshooting Guide, Best Practice, Tutorial)
- tech_stack: 관련 기술 스택 배열 (예: ["Next.js", "Python", "Docker"])

반드시 JSON 배열 형식으로만 출력하세요.

데이터:
{contents}
"""
        try:
            raw_cards = await self.llm_router.generate(prompt, provider=_default_text_provider())
            # JSON 배열 추출
            start = raw_cards.find("[")
            end = raw_cards.rfind("]") + 1
            return json.loads(raw_cards[start:end])
        except Exception as e:
            return [{"title": "지식 생성 실패", "content": str(e), "category": "Error"}]
