from typing import List, Dict, Any
from services.llm_router import LLMRouter

class TemplateManager:
    def __init__(self):
        self.llm_router = LLMRouter()

    async def generate_template_from_knowledge(self, domain: str, knowledge_list: List[Dict[str, Any]]) -> str:
        knowledge_summary = "\n".join([f"- {k['title']}: {k['summary']}" for k in knowledge_list])
        
        prompt = f"""
        당신은 시니어 AI Ops 엔지니어입니다. 다음 지식 데이터를 기반으로 '{domain}' 운영을 위한 통합 운영 가이드 템플릿(unified-ops.md)을 작성하세요.
        이 템플릿은 AGENTS.md, Skill.md, Rule.md 구성을 포함해야 합니다.
        
        [데이터]
        {knowledge_summary}
        
        [요구사항]
        1. 각 항목마다 왜 이 규칙/기술이 추가되었는지 주석을 달 것.
        2. 에이전트 역할 분리를 명시할 것 (Oracle, Librarian, Explore, Visual-Engineering, Sisyphus-Junior, Metis, Momus).
        3. 마크다운 형식으로 작성할 것.
        """
        
        return await self.llm_router.generate(prompt, provider="groq")
