from importlib import import_module
from typing import Any

from config import settings


def _load_llm_router_dependencies() -> tuple[Any, Any]:
    try:
        module = import_module("backend.services.llm_router")
    except ModuleNotFoundError:
        module = import_module("services.llm_router")
    return module.LLMRouter, module.LLMRouterError


LLMRouter, LLMRouterError = _load_llm_router_dependencies()


def _default_text_provider() -> str:
    if settings.GOOGLE_AI_STUDIO_KEY:
        return "gemini"
    if settings.POLLINATIONS_API_KEY:
        return "pollinations"
    if settings.GROQ_API_KEY:
        return "groq"
    if settings.OPENROUTER_API_KEY:
        return "openrouter"
    if settings.HUGGINGFACE_TOKEN:
        return "huggingface"
    return "pollinations"


class TemplateManager:
    def __init__(self):
        self.llm_router = LLMRouter()

    def _fallback_unified_ops(self, domain: str, knowledge_list: list[dict[str, Any]]) -> str:
        snippets = [
            f"- {k.get('title', '')}: {(k.get('summary') or k.get('content') or '')[:140]}"
            for k in knowledge_list[:15]
        ]
        evidence = "\n".join(snippets) if snippets else "- 데이터 없음"
        return (
            f"# {domain} unified-ops\n\n"
            "## 목적\n"
            "이 문서는 하네스 운영(OpenCode/Claude Code) 기준으로 도메인 운용 절차를 정리합니다.\n\n"
            "## AGENTS.md\n"
            "- Sisyphus-Junior: 실행 자동화\n"
            "- Explore/Librarian: 코드/문서 탐색\n"
            "- Oracle/Metis/Momus: 고난도 검토\n\n"
            "## Rule.md\n"
            "- 크롤링 → 분류 → 요약 → 검증 파이프라인 유지\n"
            "- 실전 운용 카테고리는 runbook/playbook/incident/deploy 맥락에서만 사용\n\n"
            "## Skill.md\n"
            "- 도메인별 추천 모델 라우팅/워크플로우를 운영 정책으로 관리\n\n"
            "## 근거 데이터\n"
            f"{evidence}\n"
        )

    async def _generate_readme(self, domain: str, knowledge_list: list[dict[str, Any]], template_content: str) -> str:
        summary_lines = "\n".join(
            [f"- {k.get('title', '')}: {(k.get('summary') or k.get('content') or '')[:120]}" for k in knowledge_list[:10]]
        )
        prompt = f"""
        '{domain}' 도메인 운영 템플릿 저장소용 README.md를 작성하세요.

        요구사항:
        - 한국어 문서
        - 섹션: 개요, 포함 파일, 빠른 시작, 추천 워크플로우, 주의사항
        - 마크다운만 출력

        지식 요약:
        {summary_lines}

        템플릿 초안 일부:
        {template_content[:1200]}
        """
        try:
            return await self.llm_router.generate(prompt, provider=_default_text_provider())
        except Exception:
            return (
                f"# {domain} 운영 템플릿\n\n"
                "## 개요\n"
                "이 저장소는 데이터 기반 추천 설정과 운영 템플릿을 제공합니다.\n\n"
                "## 포함 파일\n"
                "- unified-ops.md\n- AGENTS.md\n- Rule.md\n\n"
                "## 빠른 시작\n"
                "1. 템플릿 파일을 검토\n2. 팀 운영 규칙 반영\n3. 크롤링/분석 파이프라인과 연동\n"
            )

    def build_clone_script(self, domain: str) -> str:
        safe = domain.replace(" ", "-").replace("/", "-").lower()
        return (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n\n"
            f"REPO_NAME=\"{safe}-ops-template\"\n"
            "mkdir -p \"$REPO_NAME\"\n"
            "cd \"$REPO_NAME\"\n"
            "git init\n"
            "echo \"Template scaffold initialized\"\n"
            "echo \"Copy unified-ops.md, AGENTS.md, Rule.md, README.md here\"\n"
        )

    async def generate_template_bundle(self, domain: str, knowledge_list: list[dict[str, Any]]) -> dict[str, str]:
        # ZIP 번들은 LLM 장애 시에도 생성되도록 강한 폴백을 보장한다.
        try:
            unified_ops = await self.generate_template_from_knowledge(domain, knowledge_list)
        except Exception:
            unified_ops = self._fallback_unified_ops(domain, knowledge_list)

        readme = await self._generate_readme(domain, knowledge_list, unified_ops)
        clone_script = self.build_clone_script(domain)

        agents_md = "# Agent Definitions\n\nGenerated from context."
        rule_md = "# Project Rules\n\nGenerated from context."

        return {
            "unified-ops.md": unified_ops,
            "AGENTS.md": agents_md,
            "Rule.md": rule_md,
            "README.md": readme,
            "clone.sh": clone_script,
        }

    async def generate_template_from_knowledge(self, domain: str, knowledge_list: list[dict[str, Any]]) -> str:
        knowledge_summary = "\n".join(
            [
                f"- {k.get('title', '')}: {k.get('summary') or k.get('content') or ''}"
                for k in knowledge_list
            ]
        )
        
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
        
        try:
            return await self.llm_router.generate(prompt, provider=_default_text_provider())
        except LLMRouterError as exc:
            raise RuntimeError(f"템플릿 생성 실패 ({exc.provider}): {exc.message}") from exc

    async def generate_template(self, tech_stack: str) -> str:
        return await self.generate_template_from_knowledge(
            tech_stack,
            [{"title": tech_stack, "summary": f"{tech_stack} 운영 템플릿 기본 가이드"}],
        )
