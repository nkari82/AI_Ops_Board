from typing import Dict, Any, Optional, List
from .llm_router import LLMRouter
from models import Domain
import re


class ContentAnalyzer:
    def __init__(self):
        self.llm_router = LLMRouter()
    
    async def analyze(
        self,
        content: str,
        source_url: str,
        domain: Optional[Domain] = None
    ) -> Dict[str, Any]:
        summary = await self._generate_summary(content)
        
        score = self._calculate_score(content, summary)
        
        tags = await self._extract_tags(content, summary)
        
        related_concepts = await self._suggest_related_concepts(content, summary)
        
        risk = self._assess_risk(content, summary)
        
        category = self._classify_category(content, summary)
        
        return {
            "summary": summary,
            "score": score,
            "tags": tags,
            "related_concepts": related_concepts,
            "risk": risk,
            "category": category,
            "domain": domain.value if domain else "일반",
            "source_url": source_url
        }
    
    async def _generate_summary(self, content: str) -> str:
        prompt = f"""다음 기술 문서를 한국어로 간결하게 요약하세요. 
핵심 내용만 2-3문장으로 작성하세요.

문서:
{content[:1000]}

요약:"""
        
        try:
            summary = await self.llm_router.generate(
                prompt=prompt,
                provider="groq",
                max_tokens=200,
                temperature=0.5
            )
            return summary.strip()
        except Exception:
            return self._fallback_summary(content)
    
    def _fallback_summary(self, content: str) -> str:
        sentences = re.split(r'[.!?]\s+', content[:500])
        return '. '.join(sentences[:2]) + '.'
    
    def _calculate_score(self, content: str, summary: str) -> int:
        score = 50
        
        keywords = ['optimization', '최적화', 'performance', '성능', 'best practice', '베스트 프랙티스']
        for keyword in keywords:
            if keyword.lower() in content.lower() or keyword.lower() in summary.lower():
                score += 10
        
        if len(content) > 500:
            score += 10
        
        if 'example' in content.lower() or '예제' in content:
            score += 5
        
        return min(score, 100)
    
    async def _extract_tags(self, content: str, summary: str) -> List[str]:
        prompt = f"""다음 기술 문서와 요약본을 분석하여, 이 문서의 핵심 주제를 나타내는 태그를 5개 추출하세요.
태그는 쉼표로 구분하여 출력하세요. (예: LLM, Python, 최적화, Docker, 보안)

문서: {content[:500]}
요약: {summary}

태그:"""
        try:
            tags_str = await self.llm_router.generate(
                prompt=prompt,
                provider="groq",
                max_tokens=50,
                temperature=0.3
            )
            tags = [tag.strip() for tag in tags_str.split(',')]
            return tags[:5]
        except Exception:
            # Fallback to existing keyword-based method if LLM fails
            return self._fallback_extract_tags(content, summary)

    def _fallback_extract_tags(self, content: str, summary: str) -> List[str]:
        text = (content + " " + summary).lower()
        
        tag_keywords = {
            'vllm': ['vllm'],
            'llm': ['llm', 'language model'],
            'gpu': ['gpu', 'cuda', 'nvidia'],
            'unity': ['unity'],
            'unreal': ['unreal'],
            'react': ['react'],
            'nextjs': ['next.js', 'nextjs'],
            'python': ['python'],
            'typescript': ['typescript'],
            'docker': ['docker'],
            'kubernetes': ['k8s', 'kubernetes'],
            '최적화': ['optimization', '최적화', 'optimize'],
            '메모리': ['memory', '메모리'],
            '성능': ['performance', '성능'],
        }
        
        tags = []
        for tag, keywords in tag_keywords.items():
            if any(kw in text for kw in keywords):
                tags.append(tag)
        
        return tags[:5]
    
    async def _suggest_related_concepts(self, content: str, summary: str) -> List[str]:
        prompt = f"""다음 기술 문서와 요약본을 분석하여, 이 문서와 함께 학습하면 좋은 관련 기술 개념 3가지를 추천하세요.
        쉼표로 구분하여 출력하세요. (예: 시스템 설계, 분산 처리, 고가용성)

        문서: {content[:500]}
        요약: {summary}

        개념:"""
        try:
            concepts_str = await self.llm_router.generate(
                prompt=prompt,
                provider="groq",
                max_tokens=50,
                temperature=0.3
            )
            concepts = [c.strip() for c in concepts_str.split(',')]
            return concepts[:3]
        except Exception:
            return []
    async def _assess_risk(self, content: str, summary: str) -> str:
        text = (content + " " + summary).lower()
        
        high_risk_keywords = ['memory leak', 'crash', 'security', '보안', 'critical', 'oom']
        medium_risk_keywords = ['deprecated', 'warning', '주의', 'caution']
        
        for keyword in high_risk_keywords:
            if keyword in text:
                return "high"
        
        for keyword in medium_risk_keywords:
            if keyword in text:
                return "medium"
        
        return "low"
    
    def _classify_category(self, content: str, summary: str) -> str:
        text = (content + " " + summary).lower()
        
        if any(kw in text for kw in ['architecture', '아키텍처', 'design pattern']):
            return "아키텍처"
        elif any(kw in text for kw in ['real world', '실전', 'production']):
            return "실전 사례"
        elif any(kw in text for kw in ['tip', '팁', 'trick']):
            return "깨알팁"
        elif any(kw in text for kw in ['warning', '주의', 'pitfall', '함정']):
            return "주의/함정"
        elif any(kw in text for kw in ['plugin', 'mcp', '플러그인']):
            return "플러그인/MCP"
        else:
            return "실전 운용"
