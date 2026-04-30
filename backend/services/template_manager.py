from importlib import import_module
import json
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
            "echo \"Initializing git repository in current template directory...\"\n"
            "rm -f clone.sh\n"
            "git init\n"
            "git add .\n"
            "git commit -m \"feat: initialize harness ops template\" || true\n"
            "echo \"✅ Template repository initialized in current directory\"\n"
            "echo \"Suggested repo name: $REPO_NAME\"\n"
            "echo \"Next: edit AGENTS.md / Rule.md and push to your remote\"\n"
        )

    async def generate_template_bundle(
        self,
        domain: str,
        knowledge_list: list[dict[str, Any]],
        recommendation: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        # ZIP 번들은 LLM 장애 시에도 생성되도록 강한 폴백을 보장한다.
        try:
            unified_ops = await self.generate_template_from_knowledge(domain, knowledge_list)
        except Exception:
            unified_ops = self._fallback_unified_ops(domain, knowledge_list)

        readme = await self._generate_readme(domain, knowledge_list, unified_ops)
        clone_script = self.build_clone_script(domain)

        recommendation = recommendation or {}

        model_routing = [str(x).strip() for x in recommendation.get("modelRouting", []) if str(x).strip()]
        workflow = [str(x).strip() for x in recommendation.get("workflow", []) if str(x).strip()]
        mcp = [str(x).strip() for x in recommendation.get("mcp", []) if str(x).strip()]
        rules = [str(x).strip() for x in recommendation.get("rules", []) if str(x).strip()]
        reason = str(recommendation.get("reason") or "").strip()
        harness_type = str(recommendation.get("harnessType") or "OpenCode").strip() or "OpenCode"
        subagent_candidates = [str(x).strip() for x in recommendation.get("subagentCandidates", []) if str(x).strip()]
        official_categories_payload = recommendation.get("officialCategories") if isinstance(recommendation.get("officialCategories"), dict) else {}
        official_opencode_categories = [str(x).strip() for x in official_categories_payload.get("opencode", []) if str(x).strip()]
        official_claude_categories = [str(x).strip() for x in official_categories_payload.get("claudecode", []) if str(x).strip()]

        evidence_lines = [
            f"- {k.get('title', '')}: {(k.get('summary') or k.get('content') or '')[:140]}"
            for k in knowledge_list[:20]
        ]
        evidence_block = "\n".join(evidence_lines) if evidence_lines else "- 데이터 없음"

        agents_md = (
            f"# AGENTS.md ({domain})\n\n"
            "## 목표\n"
            "- 크롤링 데이터 기반으로 운영 가능한 하네스 산출물을 빠르게 생성/검증\n\n"
            "## Agent Roster\n"
            "- Sisyphus-Junior: 구현 실행 및 반복 검증\n"
            "- Explore: 코드베이스 탐색/패턴 수집\n"
            "- Librarian: 외부 문서/OSS 참조 확인\n"
            "- Oracle: 고난도 설계/디버깅 자문\n"
            "- Metis: 계획 전 리스크 분석\n"
            "- Momus: 계획/품질 리뷰\n\n"
            "## 운영 흐름\n"
            + ("\n".join([f"{idx+1}. {step}" for idx, step in enumerate(workflow[:8])]) + "\n\n" if workflow else "1. Crawl/Normalize\n2. Analyze\n3. Recommendation refresh\n4. Template export\n5. Smoke/Re-check\n\n")
            + "## 추천 근거\n"
            + (f"- {reason}\n" if reason else "")
            + "\n## 근거 데이터 샘플\n"
            + f"{evidence_block}\n"
        )

        rule_md = (
            f"# Rule.md ({domain})\n\n"
            "## 필수 규칙\n"
            "- 실전 운용 카테고리는 runbook/playbook/incident/deploy 맥락에서만 사용\n"
            "- LLM 실패 문자열(API 오류/timeout 등)은 저장 전에 제거\n"
            "- 크롤 후 추천 캐시를 갱신하고 freshness를 검증\n"
            "- release:full + smoke:api를 게이트로 유지\n\n"
            "## 템플릿 품질 규칙\n"
            "- 다운로드 결과는 즉시 실행 가능한 구조(README/AGENTS/Rule/clone.sh 포함)\n"
            "- 도메인별 추천 라우팅/워크플로우를 문서에 명시\n"
            + ("\n## 추천 Rules\n" + "\n".join([f"- {r}" for r in rules[:10]]) + "\n" if rules else "")
        )

        dynamic_skill_files = {
            f"skill-{idx+1:02d}-{item.lower().replace(' ', '-').replace('/', '-')}/SKILL.md": (
                "---\n"
                f"name: {item}\n"
                "description: recommendation-driven domain skill\n"
                "---\n\n"
                f"# Skill {idx+1}: {item}\n\n"
                f"- domain: {domain}\n"
                f"- harness: {harness_type}\n"
                "- 목적: 추천 셋팅 기반 운영 액션 표준화\n"
            )
            for idx, item in enumerate(mcp[:12])
        }

        opencode_category_files = {
            f".opencode/skills/category-{idx+1:02d}-{item.lower().replace(' ', '-').replace('/', '-')}/SKILL.md": (
                "---\n"
                f"name: {item}\n"
                "description: official category aligned skill\n"
                "---\n\n"
                f"# OpenCode Category: {item}\n\n"
                "- source: https://opencode.ai/docs/config\n"
                f"- domain: {domain}\n"
                "- objective: .opencode 운영 셋팅 카테고리 표준화\n"
            )
            for idx, item in enumerate(official_opencode_categories[:16])
        }

        claude_category_files = {
            f".claude/skills/category-{idx+1:02d}-{item.lower().replace(' ', '-').replace('/', '-')}/SKILL.md": (
                "---\n"
                f"name: {item}\n"
                "description: official category aligned skill\n"
                "---\n\n"
                f"# Claude Category: {item}\n\n"
                "- source: https://code.claude.com/docs/en/configuration\n"
                f"- domain: {domain}\n"
                "- objective: .claude 운영 셋팅 카테고리 표준화\n"
            )
            for idx, item in enumerate(official_claude_categories[:16])
        }

        if harness_type == "ClaudeCode":
            claude_settings = json.dumps(
                {
                    "$schema": "https://json.schemastore.org/claude-code-settings.json",
                    "env": {"OPS_DOMAIN": domain},
                    "model": model_routing[0] if model_routing else "",
                    "permissions": {"mode": "plan"},
                },
                ensure_ascii=False,
                indent=2,
            )
            claude_md = (
                f"# CLAUDE.md ({domain})\n\n"
                "## Goal\n"
                "- 추천 셋팅 기반 하네스 운영\n\n"
                "## Workflow\n"
                + ("\n".join([f"- {step}" for step in workflow[:10]]) if workflow else "- 기본 워크플로우 사용")
                + "\n\n"
                "## Rules\n"
                + ("\n".join([f"- {r}" for r in rules[:12]]) if rules else "- 기본 규칙 사용")
                + "\n"
            )
            claude_dynamic_agents = {
                f".claude/agents/dynamic-{idx+1:02d}.md": (
                    f"# Dynamic Subagent: {name}\n\n"
                    f"- domain: {domain}\n"
                    "- role: recommendation-driven dynamic specialist\n"
                )
                for idx, name in enumerate(subagent_candidates[:12])
            }
            claude_dynamic_skills = {
                f".claude/skills/{path}": content
                for path, content in dynamic_skill_files.items()
            }

            return {
                ".claude/README.md": readme,
                ".claude/CLAUDE.md": claude_md,
                ".claude/settings.json": claude_settings,
                ".claude/unified-ops.md": unified_ops,
                ".claude/Rule.md": rule_md,
                ".claude/clone.sh": clone_script,
                **claude_dynamic_agents,
                **claude_dynamic_skills,
                **claude_category_files,
            }

        opencode_config = json.dumps(
            {
                "$schema": "https://opencode.ai/config.json",
                "agent": {
                    "build": {
                        "description": f"{domain} recommendation operator",
                    }
                },
                "command": {
                    "start-work": {
                        "description": "추천 셋팅 기반 작업 시작",
                        "template": "Run start-work checklist"
                    },
                    "review-work": {
                        "description": "품질 게이트 점검",
                        "template": "Run review-work checklist"
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        )

        opencode_start_work = (
            f"# /start-work ({domain})\n\n"
            "## Goal\n- 추천 셋팅 기반 작업 시작\n\n"
            "## Steps\n"
            + ("\n".join([f"- {step}" for step in workflow[:10]]) if workflow else "- 기본 워크플로우 사용")
            + "\n"
        )
        opencode_review_work = (
            f"# /review-work ({domain})\n\n"
            "## Gate\n- build/smoke 통과 확인\n"
            "- 규칙 위반(as any, ts-ignore) 점검\n"
        )

        opencode_dynamic_agents = {
            f".opencode/agents/dynamic-{idx+1:02d}.md": (
                f"# Dynamic Agent: {name}\n\n"
                f"- domain: {domain}\n"
                "- role: recommendation-driven dynamic specialist\n"
            )
            for idx, name in enumerate(subagent_candidates[:12])
        }

        opencode_dynamic_skills = {
            f".opencode/skills/{path}": content
            for path, content in dynamic_skill_files.items()
        }

        return {
            ".opencode/README.md": readme,
            ".opencode/AGENTS.md": agents_md,
            ".opencode/Rule.md": rule_md,
            ".opencode/unified-ops.md": unified_ops,
            ".opencode/clone.sh": clone_script,
            "opencode.json": opencode_config,
            ".opencode/commands/start-work.md": opencode_start_work,
            ".opencode/commands/review-work.md": opencode_review_work,
            **opencode_dynamic_agents,
            **opencode_dynamic_skills,
            **opencode_category_files,
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
