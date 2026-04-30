from __future__ import annotations

import json
import re
from importlib import import_module
from typing import Any

from .llm_router import LLMRouter


def _load_domain_enum() -> Any:
    try:
        return import_module("backend.models").Domain
    except ModuleNotFoundError:
        return import_module("models").Domain


Domain = _load_domain_enum()


def _load_settings() -> Any:
    try:
        return import_module("backend.config").settings
    except ModuleNotFoundError:
        return import_module("config").settings


_SETTINGS = _load_settings()


_BOARD_CATEGORIES: list[str] = [
    "실전 운용",
    "아키텍처",
    "실전 사례",
    "깨알팁",
    "주의/함정",
    "플러그인/MCP",
]

_DOMAINS: list[str] = [
    "게임 클라이언트",
    "게임 서버",
    "프론트엔드",
    "백엔드",
    "Unity",
    "Unreal",
    "로컬 LLM",
    "Agent/MCP",
    "기타",
]


class ContentAnalyzer:
    def __init__(self):
        self.llm_router = LLMRouter()

    def _default_text_provider(self) -> str:
        # Prefer free/cheap providers for analysis tasks
        if getattr(_SETTINGS, "GOOGLE_AI_STUDIO_KEY", None):
            return "gemini"
        if getattr(_SETTINGS, "POLLINATIONS_API_KEY", None):
            return "pollinations"
        if getattr(_SETTINGS, "GROQ_API_KEY", None):
            return "groq"
        if getattr(_SETTINGS, "OPENROUTER_API_KEY", None):
            return "openrouter"
        if getattr(_SETTINGS, "MISTRAL_API_KEY", None):
            return "mistral"
        if getattr(_SETTINGS, "DEEPSEEK_API_KEY", None):
            return "deepseek"
        if getattr(_SETTINGS, "CEREBRAS_API_KEY", None):
            return "cerebras"
        if getattr(_SETTINGS, "SAMBANOVA_API_KEY", None):
            return "sambanova"
        if getattr(_SETTINGS, "HUGGINGFACE_TOKEN", None):
            return "huggingface"
        return "gemini"
    
    async def analyze(
        self,
        content: str,
        source_url: str,
        domain: Any | None = None,
        *,
        title: str | None = None,
    ) -> dict[str, Any]:
        """LLM 기반 지식 카드 분석.

        목표:
        - 단일 LLM 호출로 `title_ko`, `summary_ko`, `category`, `domain`을 생성(가능하면)
        - 실패 시 기존(분리된) 분류/요약 로직으로 폴백
        """
        normalized_content = (content or "").strip()
        domain_hint = domain.value if domain else None

        card_fields = await self._classify_card_fields(
            title=(title or "").strip(),
            content=normalized_content,
            domain_hint=domain_hint,
        )

        summary_ko = (card_fields.get("summary_ko") or "").strip()
        if self._looks_like_llm_failure(summary_ko):
            summary_ko = ""
        if not summary_ko:
            summary_ko = await self._generate_summary(normalized_content)

        category = (card_fields.get("category") or "").strip()
        if self._looks_like_llm_failure(category) or category not in _BOARD_CATEGORIES:
            category = await self._classify_category(normalized_content, summary_ko)
        category = self._normalize_operational_category(category, normalized_content, summary_ko)

        domain_value = (card_fields.get("domain") or "").strip()
        if self._looks_like_llm_failure(domain_value) or domain_value not in _DOMAINS:
            domain_value = await self._classify_domain(normalized_content, summary_ko, domain_hint)

        title_ko = (card_fields.get("title_ko") or "").strip()
        if self._looks_like_llm_failure(title_ko):
            title_ko = ""
        original_title = (title or "").strip()
        if not title_ko:
            title_ko = original_title

        # LLM 호출 최소화: title/summary는 1차 구조화 호출 결과를 우선 사용하고 추가 번역 호출은 생략
        if original_title and not self._contains_korean(title_ko):
            # 한국어가 아닌 원문 제목은 title_ko에 그대로 저장하지 않고 원문 유지 fallback만 수행
            title_ko = original_title

        if summary_ko and not self._contains_korean(summary_ko):
            summary_ko = self._fallback_summary(normalized_content)
        score = self._calculate_score(normalized_content, summary_ko)

        tags_from_structured = card_fields.get("tags")
        if isinstance(tags_from_structured, list):
            tags = [str(x).strip() for x in tags_from_structured if str(x).strip()][:5]
        else:
            tags = await self._extract_tags(normalized_content, summary_ko)

        tech_from_structured = card_fields.get("tech_stack")
        if isinstance(tech_from_structured, list):
            tech_stack = [str(x).strip() for x in tech_from_structured if str(x).strip()][:3]
        else:
            tech_stack = await self._extract_tech_stack(normalized_content, summary_ko)

        related_concepts = await self._suggest_related_concepts(normalized_content, summary_ko)
        risk = self._assess_risk(normalized_content, summary_ko)
        doc_type = self._classify_type(normalized_content, summary_ko)

        return {
            "title_ko": title_ko,
            "summary_ko": summary_ko,
            "summary": summary_ko,  # 하위 호환: summary는 항상 한글 요약을 유지
            "score": score,
            "tags": tags,
            "related_concepts": related_concepts,
            "risk": risk,
            "category": category,
            "type": doc_type,
            "tech_stack": tech_stack,
            "domain": domain_value,
            "source_url": source_url,
        }

    def _contains_korean(self, text: str) -> bool:
        return bool(re.search(r"[가-힣]", text or ""))

    def _has_operational_markers(self, content: str, summary: str) -> bool:
        text = ((content or "") + "\n" + (summary or "")).lower()
        strong_ops_markers = [
            "runbook", "on-call", "oncall", "monitor", "alert", "incident", "postmortem",
            "deploy", "deployment", "release", "sre", "playbook", "checklist", "template",
            "운영", "운용", "플레이북", "체크리스트", "템플릿", "하네스",
            "opencode", "open code", "claude code", "agent orchestration", "toolchain",
        ]
        return any(marker in text for marker in strong_ops_markers)

    def _has_harness_tool_markers(self, content: str, summary: str) -> bool:
        text = ((content or "") + "\n" + (summary or "")).lower()
        markers = [
            "opencode", "open code", "claude code", "mcp", "agent", "tool-use", "tool use",
            "harness", "workflow", "orchestr", "prompt chain", "automation",
        ]
        return any(marker in text for marker in markers)

    def _normalize_operational_category(self, category: str, content: str, summary: str) -> str:
        """'실전 운용'은 하네스/운영 템플릿 성격일 때만 허용."""
        if category != "실전 운용":
            return category if category in _BOARD_CATEGORIES else "깨알팁"
        return "실전 운용" if self._has_operational_markers(content, summary) else "깨알팁"

    async def _translate_to_korean(self, text: str, *, max_chars: int) -> str:
        source = (text or "").strip()
        if not source:
            return ""
        prompt = f"""Translate the following text to natural Korean.
Return only Korean text, no explanation.

Text:
{source[:max_chars]}
"""
        strict_prompt = f"""다음 문장을 반드시 한국어로만 번역해서 출력하세요.
영어 단어만 그대로 반복하지 말고, 자연스러운 한국어 문장으로 작성하세요.
설명/따옴표/코드블록 없이 번역문만 출력하세요.

원문:
{source[:max_chars]}
"""
        try:
            translated = await self.llm_router.generate(
                prompt=prompt,
                provider=self._default_text_provider(),
                max_tokens=220,
                temperature=0.0,
            )
            translated = (translated or "").strip()
            if translated and not self._looks_like_llm_failure(translated) and self._contains_korean(translated):
                return translated

            translated2 = await self.llm_router.generate(
                prompt=strict_prompt,
                provider=self._default_text_provider(),
                max_tokens=220,
                temperature=0.0,
            )
            translated2 = (translated2 or "").strip()
            if translated2 and not self._looks_like_llm_failure(translated2) and self._contains_korean(translated2):
                return translated2
        except Exception:
            pass
        return source

    def _looks_like_llm_failure(self, text: str) -> bool:
        normalized = (text or "").strip().lower()
        if not normalized:
            return True
        failure_markers = [
            "llm 생성 실패",
            "api 오류",
            "토큰이 설정되지 않았습니다",
            "api key",
            "status code",
            "authentication",
            "unauthorized",
            "forbidden",
            "rate limit",
            "timeout",
        ]
        return any(marker in normalized for marker in failure_markers)

    def _parse_llm_list(self, raw_text: str, limit: int) -> list[str]:
        if self._looks_like_llm_failure(raw_text):
            return []

        items = [item.strip() for item in raw_text.split(",")]
        cleaned: list[str] = []
        for item in items:
            if not item or self._looks_like_llm_failure(item):
                continue
            if item not in cleaned:
                cleaned.append(item)
        return cleaned[:limit]

    def _extract_json_field(self, raw_text: str, field: str) -> str | None:
        text = (raw_text or "").strip()
        if not text:
            return None
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                obj = json.loads(text[start : end + 1])
                value = obj.get(field)
                return value if isinstance(value, str) else None
        except Exception:
            return None
        return None

    def _extract_json_object(self, raw_text: str) -> dict[str, Any] | None:
        text = (raw_text or "").strip()
        if not text:
            return None
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                obj = json.loads(text[start : end + 1])
                return obj if isinstance(obj, dict) else None
        except Exception:
            return None
        return None

    def _extract_delimited_card_fields(self, raw_text: str) -> dict[str, Any]:
        text = (raw_text or "").strip()
        if not text:
            return {}

        def pick(tag: str) -> str | None:
            m = re.search(rf"\[{tag}\]([\s\S]*?)\[/{tag}\]", text)
            if not m:
                return None
            value = m.group(1).strip()
            return value or None

        result: dict[str, Any] = {}
        for field, tag in [
            ("title_ko", "TITLE_KO"),
            ("summary_ko", "SUMMARY_KO"),
            ("category", "CATEGORY"),
            ("domain", "DOMAIN"),
        ]:
            value = pick(tag)
            if value:
                result[field] = value

        tags = pick("TAGS")
        tech_stack = pick("TECH_STACK")
        if tags:
            result["tags"] = self._parse_llm_list(tags, limit=5)
        if tech_stack:
            result["tech_stack"] = self._parse_llm_list(tech_stack, limit=3)

        return result

    async def _classify_card_fields(
        self,
        *,
        title: str,
        content: str,
        domain_hint: str | None,
    ) -> dict[str, Any]:
        """단일 LLM 호출로 카드 핵심 필드 JSON을 생성.

        기대 JSON(+구분자 폴백):
        {
          "title_ko": "...",
          "summary_ko": "...",  // 2~3줄 한글 요약
          "category": "...",    // _BOARD_CATEGORIES 중 1개
          "domain": "...",      // _DOMAINS 중 1개
          "tags": ["..."],
          "tech_stack": ["..."]
        }
        """
        text = (content or "").strip()
        if not title and not text:
            return {}

        hint = (domain_hint or "").strip()

        prompt = f"""You are a strict JSON generator for a knowledge card.

Return JSON ONLY with the following keys:
- title_ko: Korean translation of the title. If the title is already Korean, keep it.
- summary_ko: 2~3 lines Korean summary of the content.
- category: choose exactly one from the allowed list.
- domain: choose exactly one from the allowed list.
- tags: max 5 items (string list)
- tech_stack: max 3 items (string list)

Allowed categories:
{json.dumps(_BOARD_CATEGORIES, ensure_ascii=False)}

Allowed domains:
{json.dumps(_DOMAINS, ensure_ascii=False)}

Category guidance:
- "실전 운용" ONLY for harness-style operational templates/playbooks: monitoring/alerts, incident response, deployment/release, SRE 운영 절차, 체크리스트.
- "아키텍처" for system design, patterns, component boundaries.
- "실전 사례" for case studies / postmortems.
- "깨알팁" for small actionable tips.
- "주의/함정" for pitfalls / warnings / security footguns.
- "플러그인/MCP" for MCP/plugins/integrations/tooling extensions.

OpenCode/Claude Code baseline rule:
- If text is about OpenCode/Claude Code agent workflows/tooling, prefer domain "Agent/MCP".
- Use category "실전 운용" ONLY when it describes reusable harness operations templates/runbooks.
- Otherwise classify as "플러그인/MCP", "깨알팁", "주의/함정", "실전 사례", or "아키텍처" based on substance.

If hint matches one of allowed domains, you may use it unless the text clearly points elsewhere.
Hint: {hint}

Title:
{title[:300]}

Content:
{text[:2500]}

If you cannot produce JSON, output with exact delimiters below:
[TITLE_KO]...[/TITLE_KO]
[SUMMARY_KO]...[/SUMMARY_KO]
[CATEGORY]...[/CATEGORY]
[DOMAIN]...[/DOMAIN]
[TAGS]tag1,tag2[/TAGS]
[TECH_STACK]tech1,tech2[/TECH_STACK]
"""
        try:
            raw = await self.llm_router.generate(
                prompt=prompt,
                provider=self._default_text_provider(),
                max_tokens=300,
                temperature=0.0,
            )
            obj = self._extract_json_object(raw)
            result: dict[str, Any] = {}
            if obj:
                for key in ["title_ko", "summary_ko", "category", "domain"]:
                    value = obj.get(key)
                    if isinstance(value, str) and value.strip():
                        result[key] = value.strip()

                tags = obj.get("tags")
                tech_stack = obj.get("tech_stack")
                if isinstance(tags, list):
                    result["tags"] = [str(x).strip() for x in tags if str(x).strip()][:5]
                if isinstance(tech_stack, list):
                    result["tech_stack"] = [str(x).strip() for x in tech_stack if str(x).strip()][:3]
            else:
                result = self._extract_delimited_card_fields(raw)

            # Validate label constraints; if invalid, drop so caller falls back
            if result.get("category") not in _BOARD_CATEGORIES:
                result.pop("category", None)
            if result.get("domain") not in _DOMAINS:
                result.pop("domain", None)

            return result
        except Exception:
            return {}

    async def _classify_domain(self, content: str, summary: str, domain_hint: str | None) -> str:
        """카테고리 2축(도메인) 분류: 반드시 _DOMAINS 중 하나를 반환."""
        text = (content + "\n" + summary).strip()
        hint = (domain_hint or "").strip()
        if not text and hint in _DOMAINS:
            return hint

        prompt = f"""You are a strict classifier.
Choose exactly ONE domain from the allowed list.

Allowed domains:
{json.dumps(_DOMAINS, ensure_ascii=False)}

Guidance:
- 게임 클라이언트: 클라이언트 런타임, 렌더링, 입력, 최적화, 빌드, 플랫폼 이슈.
- 게임 서버: 서버 아키텍처, 네트워킹, 동기화, DB, 스케일링.
- 프론트엔드: Web UI, React/Next.js, FE tooling.
- 백엔드: API, DB, infra backend, FastAPI 등.
- Unity / Unreal: 엔진 특정.
- 로컬 LLM: vLLM/llama.cpp/모델 서빙/추론 최적화.
- Agent/MCP: 에이전트, MCP, tool-use, orchestration.

OpenCode/Claude Code baseline rule:
- Mentions of OpenCode, Claude Code, MCP agent workflows, or harness-style automation should generally map to domain "Agent/MCP" unless the text is clearly about another technical domain.

If hint is provided and matches, you may use it unless the text clearly points elsewhere.
Hint: {hint}

Return JSON only: {{"domain": "..."}}.

Text:
{text[:2000]}
"""
        try:
            raw = await self.llm_router.generate(
                prompt=prompt,
                provider=self._default_text_provider(),
                max_tokens=60,
                temperature=0.0,
            )
            dom = self._extract_json_field(raw, "domain")
            if dom in _DOMAINS:
                return dom
        except Exception:
            pass

        # Fallback: OpenCode/Claude Code/Harness 계열은 Agent/MCP 우선
        lowered = text.lower()
        if any(kw in lowered for kw in ["opencode", "open code", "claude code", "mcp", "agent", "harness", "orchestr"]):
            return "Agent/MCP"

        # If hint is valid use it, else 기타
        return hint if hint in _DOMAINS else Domain.기타.value

    def _classify_type(self, content: str, summary: str) -> str:
        """문서 타입 분류"""
        text = (content + " " + summary).lower()
        
        if any(kw in text for kw in ['how to', 'tutorial', '튜토리얼', 'guide']):
            return "Tutorial"
        elif any(kw in text for kw in ['error', 'issue', 'troubleshoot', '문제 해결']):
            return "Troubleshooting Guide"
        elif any(kw in text for kw in ['best practice', '베스트 프랙티스', 'pattern']):
            return "Best Practice"
        else:
            return "Knowledge Article"

    async def _extract_tech_stack(self, content: str, summary: str) -> list[str]:
        """기술 스택 추출 (LLM 기반)"""
        prompt = f"""다음 기술 문서에서 사용된 주요 기술 스택(프레임워크, 언어, 도구)을 추출하세요.
최대 3개, 쉼표로 구분하여 출력하세요. (예: Next.js, Python, Docker)

문서: {content[:500]}
요약: {summary}

기술 스택:"""
        
        try:
            tech_str = await self.llm_router.generate(
                prompt=prompt,
                provider=self._default_text_provider(),
                max_tokens=50,
                temperature=0.3
            )
            tech_stack = self._parse_llm_list(tech_str, limit=3)
            return tech_stack or self._fallback_tech_stack(content, summary)
        except Exception:
            return self._fallback_tech_stack(content, summary)

    def _fallback_tech_stack(self, content: str, summary: str) -> list[str]:
        """기술 스택 추출 폴백 (키워드 기반)"""
        text = (content + " " + summary).lower()
        
        tech_keywords = {
            'Next.js': ['next.js', 'nextjs'],
            'React': ['react'],
            'Python': ['python'],
            'TypeScript': ['typescript'],
            'Docker': ['docker'],
            'vLLM': ['vllm'],
            'Unity': ['unity'],
            'Kubernetes': ['k8s', 'kubernetes'],
            'PostgreSQL': ['postgres', 'postgresql'],
        }
        
        found_tech = []
        for tech, keywords in tech_keywords.items():
            if any(kw in text for kw in keywords):
                found_tech.append(tech)
        
        return found_tech[:3]

    
    async def _generate_summary(self, content: str) -> str:
        if not content:
            return "요약할 원문이 없습니다."

        prompt = f"""다음 기술 문서를 한국어로 간결하게 요약하세요. 
핵심 내용만 2-3문장으로 작성하세요.

문서:
{content[:1000]}

요약:"""
        
        try:
            summary = await self.llm_router.generate(
                prompt=prompt,
                provider=self._default_text_provider(),
                max_tokens=200,
                temperature=0.5
            )
            if self._looks_like_llm_failure(summary):
                return self._fallback_summary(content)
            return summary.strip()
        except Exception:
            return self._fallback_summary(content)
    
    def _fallback_summary(self, content: str) -> str:
        if not content:
            return "요약할 원문이 없습니다."
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
    
    async def _extract_tags(self, content: str, summary: str) -> list[str]:
        prompt = f"""다음 기술 문서와 요약본을 분석하여, 이 문서의 핵심 주제를 나타내는 태그를 5개 추출하세요.
태그는 쉼표로 구분하여 출력하세요. (예: LLM, Python, 최적화, Docker, 보안)

문서: {content[:500]}
요약: {summary}

태그:"""
        try:
            tags_str = await self.llm_router.generate(
                prompt=prompt,
                provider=self._default_text_provider(),
                max_tokens=50,
                temperature=0.3
            )
            tags = self._parse_llm_list(tags_str, limit=5)
            if not tags:
                return self._fallback_extract_tags(content, summary)
            return tags[:5]
        except Exception:
            # Fallback to existing keyword-based method if LLM fails
            return self._fallback_extract_tags(content, summary)

    def _fallback_extract_tags(self, content: str, summary: str) -> list[str]:
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
    
    async def _suggest_related_concepts(self, content: str, summary: str) -> list[str]:
        prompt = f"""다음 기술 문서와 요약본을 분석하여, 이 문서와 함께 학습하면 좋은 관련 기술 개념 3가지를 추천하세요.
        쉼표로 구분하여 출력하세요. (예: 시스템 설계, 분산 처리, 고가용성)

        문서: {content[:500]}
        요약: {summary}

        개념:"""
        try:
            concepts_str = await self.llm_router.generate(
                prompt=prompt,
                provider=self._default_text_provider(),
                max_tokens=50,
                temperature=0.3
            )
            concepts = self._parse_llm_list(concepts_str, limit=3)
            return concepts[:3]
        except Exception:
            return []

    def _assess_risk(self, content: str, summary: str) -> str:
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
    
    async def _classify_category(self, content: str, summary: str) -> str:
        """카테고리 1축 분류: 반드시 _BOARD_CATEGORIES 중 하나를 반환."""
        text = (content + "\n" + summary).strip()
        if not text:
            return "깨알팁"

        # LLM-based strict classification first
        prompt = f"""You are a strict classifier.
Choose exactly ONE category from the allowed list.

Allowed categories:
{json.dumps(_BOARD_CATEGORIES, ensure_ascii=False)}

Guidance:
- "실전 운용" is ONLY for harness-style operational runbooks: monitoring/alerts, incident response, deployment/release, reliability/SRE ops, 운영 템플릿/플레이북/체크리스트.
- "아키텍처" for system design, design patterns, dataflow, scalability, component boundaries.
- "실전 사례" for postmortems, case studies, lessons from production, "we did X" narratives.
- "깨알팁" for small actionable tips, shortcuts, dev-experience improvements.
- "주의/함정" for pitfalls, gotchas, warnings, security footguns.
- "플러그인/MCP" for MCP, plugins, integrations, tooling extensions.

Return JSON only: {{"category": "..."}}.

Text:
{text[:2000]}
"""
        try:
            raw = await self.llm_router.generate(
                prompt=prompt,
                provider=self._default_text_provider(),
                max_tokens=50,
                temperature=0.0,
            )
            category = self._extract_json_field(raw, "category")
            if category in _BOARD_CATEGORIES:
                return self._normalize_operational_category(category, content, summary)
        except Exception:
            pass

        # Fallback heuristic (broader than before)
        lowered = text.lower()
        if any(kw in lowered for kw in ["opencode", "open code", "claude code", "mcp", "plugin", "플러그인", "integration", "connector", "agent", "harness", "orchestr"]):
            # 하네스 운용 템플릿 문맥이 충분히 강한 경우에만 실전 운용으로 승격
            if self._has_operational_markers(content, summary) and any(
                marker in lowered for marker in ["runbook", "playbook", "incident", "deploy", "release", "운영", "운용", "체크리스트"]
            ):
                return "실전 운용"
            return "플러그인/MCP"
        if any(kw in lowered for kw in ["pitfall", "gotcha", "warning", "주의", "함정", "caution", "security", "취약", "attack"]):
            return "주의/함정"
        if any(kw in lowered for kw in ["architecture", "아키텍처", "design pattern", "system design", "scalab", "throughput", "latency", "component", "microservice"]):
            return "아키텍처"
        if any(kw in lowered for kw in ["postmortem", "incident", "we deployed", "in production", "실전 사례", "case study"]):
            return "실전 사례"
        if any(kw in lowered for kw in ["runbook", "on-call", "monitor", "alert", "incident response", "deploy", "release", "운용", "운영", "플레이북", "체크리스트", "템플릿", "하네스"]):
            return "실전 운용"
        return "깨알팁"
