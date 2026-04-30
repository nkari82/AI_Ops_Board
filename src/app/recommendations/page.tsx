"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";

import type { Domain, RecommendedSetting } from "@/types";
import {
  downloadTemplateApi,
  fetchRecommendedSettingsApi,
  getCloneInstructionsApi,
  sendRecommendationFeedbackApi,
} from "@/lib/api";

import { RecommendedSettingCard } from "@/components/recommended/RecommendedSettingCard";
import { Button } from "@/components/ui/button";

type HarnessType = "OpenCode" | "ClaudeCode";
type ClientEngine = "유니티" | "언리얼" | "자체엔진";
type GameGenre =
  | "RPG"
  | "FPS/TPS"
  | "전략/시뮬레이션"
  | "캐주얼/하이퍼캐주얼"
  | "스포츠/레이싱"
  | "퍼즐"
  | "MMO"
  | "액션/어드벤처"
  | "기타";
type DevLanguage =
  | "C#"
  | "C++"
  | "Blueprint"
  | "Lua"
  | "TypeScript"
  | "Rust"
  | "Python"
  | "기타";

type HarnessView =
  | "pluginHook"
  | "agents"
  | "skill"
  | "rull"
  | "openCodeJsonc"
  | "claudeCodeJson"
  | "pluginMcpList"
  | "permissionsMatrix"
  | "commandsRegistry"
  | "providerConfig"
  | "toolsRegistry"
  | "formatterConfig"
  | "watcherConfig"
  | "serverConfig"
  | "compactionConfig"
  | "instructionsRegistry"
  | "configPrecedence"
  | "mcpOauthStatus"
  | "permissionModes"
  | "hooksConfig"
  | "autoMemory"
  | "rulesManager"
  | "subagentsManager"
  | "subagentPlanner"
  | "subagentImplementer"
  | "subagentReviewer"
  | "officialCategoryModel"
  | "outputStyles"
  | "sandboxConfig"
  | "modelConfig"
  | "statusLine"
  | "worktreeInclude";

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function toSlug(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9가-힣]+/g, "-").replace(/^-+|-+$/g, "");
}

function renderViewContent(
  view: HarnessView,
  harnessType: HarnessType,
  setting: RecommendedSetting | undefined,
): string {
  if (!setting) return "";

  const domain = setting.domain;
  const rules = setting.rules ?? [];
  const mcp = setting.mcp ?? [];
  const modelRouting = setting.modelRouting ?? [];
  const workflow = setting.workflow ?? [];

  const rulesMd = rules.map((r) => `- ${r}`).join("\n") || "- 규칙 데이터 없음";
  const workflowMd = workflow.map((w) => `- ${w}`).join("\n") || "- 워크플로우 데이터 없음";
  const mcpMd = mcp.map((m) => `- ${m}`).join("\n") || "- MCP/플러그인 데이터 없음";
  const routeMd = modelRouting.map((m) => `- ${m}`).join("\n") || "- 라우팅 데이터 없음";

  const baseHeader = `# ${harnessType} Harness\n\n- domain: ${domain}\n- score: ${setting.score}\n- evidence: ${setting.evidenceCount ?? 0}\n- feedback: ${setting.feedbackCount ?? 0}`;

  switch (view) {
    case "pluginHook":
      return `${baseHeader}\n\n## plugin hook\n${workflowMd}\n\n## routing\n${routeMd}`;
    case "agents":
      return `<!-- 이 파일은 하네스 운영 역할과 규칙을 한눈에 보여줍니다. -->\n# ${harnessType === "OpenCode" ? ".opencode/AGENTS.md" : ".claude/CLAUDE.md"}\n\n## 목표\n${setting.reason}\n\n## 도메인\n- ${domain}\n\n## 운영 규칙\n${rulesMd}\n\n## 작업 흐름\n${workflowMd}`;
    case "skill":
      return `<!-- 이 파일은 공식 skills 폴더에 들어갈 추천 스킬 샘플입니다. -->\n# ${harnessType === "OpenCode" ? ".opencode/skills/<name>/SKILL.md" : ".claude/skills/<name>/SKILL.md"}\n\n## Skill Set (${harnessType})\n${routeMd}\n\n## Domain Specialization\n- ${domain}\n\n## MCP / Plugins\n${mcpMd}`;
    case "rull":
      return `<!-- 이 파일은 운영 시 반드시 지켜야 할 규칙을 정의합니다. -->\n# ${harnessType === "OpenCode" ? ".opencode/Rule.md" : ".claude/Rule.md"}\n\n## Runtime Unified LLM Rules\n${rulesMd}\n\n## Guardrails\n- 실패 시 재시도/백오프\n- 상태/메트릭 가시화\n- smoke gate 통과 후 배포`;
    case "openCodeJsonc":
      return `// 이 파일은 OpenCode 공식 스키마(opencode.jsonc)에 맞춘 설정입니다.
{
  "$schema": "https://opencode.ai/config.json",
  "model": "${modelRouting[0] ?? "anthropic/claude-sonnet-4-5"}",
  "small_model": "openai/gpt-4.1-mini",
  "default_agent": "implementer",
  "instructions": [
    ".opencode/AGENTS.md",
    ".opencode/Rule.md",
    ".opencode/unified-ops.md"
  ],
  "agent": {
    "planner": { "mode": "subagent", "description": "요구사항 분석/리스크 식별" },
    "implementer": { "mode": "primary", "description": "코드/설정 수정 및 회귀 수정" },
    "reviewer": { "mode": "subagent", "description": "품질게이트/보안/회귀 검증" }
  },
  "command": {
    "start-work": {
      "template": "Read {file:.opencode/commands/start-work.md} and execute checklist",
      "agent": "implementer"
    },
    "review-work": {
      "template": "Read {file:.opencode/commands/review-work.md} and verify quality gates",
      "agent": "reviewer"
    }
  },
  "mcp": {
    "filesystem": {
      "type": "local",
      "enabled": true,
      "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "."]
    },
    "github": {
      "type": "local",
      "enabled": true,
      "command": ["npx", "-y", "@modelcontextprotocol/server-github"],
      "environment": { "GITHUB_TOKEN": "\${GITHUB_TOKEN}" }
    }
  },
  "plugin": ${JSON.stringify(mcp.slice(0, 16), null, 2)},
  "permission": { "edit": "allow", "bash": "ask", "webfetch": "ask" },
  "provider": {
    "openai": { "disabled": false },
    "anthropic": { "disabled": false }
  }
}`;
    case "claudeCodeJson":
      return `// 이 파일은 Claude Code가 공식적으로 읽는 로컬 설정 파일입니다.
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "env": {
    "OPS_DOMAIN": "${domain}"
  },
  "model": "${modelRouting[0] ?? ""}",
  "permissions": {
    "mode": "plan"
  },
  "routing": ${JSON.stringify(modelRouting, null, 2)},
  "steps": ${JSON.stringify(workflow, null, 2)},
  "rules": ${JSON.stringify(rules, null, 2)},
  "plugins": ${JSON.stringify(mcp, null, 2)}
}`;
    case "pluginMcpList":
      return `# Plugin & MCP List\n\n## Domain\n- ${domain}\n\n## Items\n${mcpMd}`;

    // OpenCode official-oriented views
    case "permissionsMatrix":
      return `# Permissions Matrix (${harnessType})\n\n- source: opencode.json.permission\n- domain: ${domain}\n\n## allow\n- Bash(npm run build)\n- Read(src/**)\n- Grep(**/*.ts)\n\n## ask\n- Edit(config/**)\n- WebFetch(domain:*)\n\n## deny\n- Bash(rm -rf *)\n\n## note\n- 에이전트별 permission override를 별도 관리`;
    case "commandsRegistry":
      return `<!-- 이 파일은 하네스 명령어를 공식 commands 폴더에서 인식시키기 위한 샘플입니다. -->\n# ${harnessType === "OpenCode" ? ".opencode/commands/start-work.md" : ".claude/commands/start-work.md"}\n\n## commands\n- /start-work\n- /review-work\n- /deploy-check\n\n## placeholders\n- $ARGUMENTS\n- $1, $2\n- @filepath\n- !\`command\``;
    case "providerConfig":
      return `# Provider Configuration\n\n- source: opencode.json.provider\n- harnessType: ${harnessType}\n\n## routing\n${routeMd}\n\n## policy\n- timeout: 15000ms\n- failover: enabled\n- disabled_providers / enabled_providers 분리\n- subscription providers: Codex CLI`;
    case "toolsRegistry":
      return `# Tools Registry\n\n## core tools\n- bash, read, write, edit, grep, glob, lsp, skill\n\n## mcp wildcard\n- mymcp_*\n- playwright_*\n\n## domain\n- ${domain}`;
    case "formatterConfig":
      return `# Formatter Configuration\n\n- source: opencode.json.formatter\n\n## example\n- prettier: [\"npx\",\"prettier\",\"--write\",\"$FILE\"]\n- extensions: .ts,.tsx,.md\n- disabled: false`;
    case "watcherConfig":
      return `# File Watcher\n\n- source: opencode.json.watcher\n\n## include\n- src/**/*.ts\n- src/**/*.tsx\n\n## exclude\n- node_modules/**\n- .git/**\n- dist/**`;
    case "serverConfig":
      return `# Server Configuration\n\n- source: opencode.json.server\n\n## values\n- host: 127.0.0.1\n- port: 4096\n- cors: [http://localhost:3000]\n- mdns: false`;
    case "compactionConfig":
      return `# Compaction Configuration\n\n- source: opencode.json.compaction\n\n## options\n- auto: true\n- prune: true\n\n## objective\n- 컨텍스트 한계 이전에 안전 압축`;
    case "instructionsRegistry":
      return `# Instructions Registry\n\n- source: opencode.json.instructions\n\n## loaded files\n- AGENTS.md\n- docs/harness-rules.md\n- remote: https://.../harness-policy.md\n\n## order\n- global -> project -> local override`;
    case "configPrecedence":
      return `# Config Precedence Viewer\n\n1. remote config\n2. global config\n3. custom env config\n4. project opencode.json\n5. .opencode directory\n6. inline content\n7. managed config\n8. os policy`;
    case "mcpOauthStatus":
      return `# MCP OAuth Status\n\n- source: ~/.local/share/opencode/mcp-auth.json\n\n## servers\n- github-mcp: authenticated\n- notion-mcp: pending\n- jira-mcp: expired\n\n## action\n- re-auth command: opencode mcp auth <server>`;

    // Claude Code official-oriented views
    case "permissionModes":
      return `# Claude Permission Modes\n\n- source: settings.json.defaultMode\n\n## modes\n- default\n- acceptEdits\n- plan\n- auto\n- dontAsk\n- bypassPermissions\n\n## current recommendation\n- production: plan\n- local dev: acceptEdits`;
    case "hooksConfig":
      return `# Claude Hooks Configuration\n\n- source: settings.json.hooks\n\n## events\n- PreToolUse\n- PostToolUse\n- WorktreeCreate\n\n## handlers\n- command hook\n- http webhook\n- prompt injection`;
    case "autoMemory":
      return `# Auto Memory Viewer\n\n- source: ~/.claude/projects/<hash>/memory/*.md\n\n## sections\n- MEMORY.md index\n- topic memory files\n\n## policy\n- project-specific memory load`;
    case "rulesManager":
      return `# Rules Manager\n\n- source: .claude/rules/*.md\n\n## path-scoped rules\n- paths: [\"src/api/**/*.ts\",\"**/*.test.ts\"]\n\n## objective\n- 파일 경로별 실행 규칙 분리`;
    case "subagentsManager":
      return `# Subagents Manager\n\n- source: ${harnessType === "ClaudeCode" ? ".claude/agents/*.md" : "opencode.json.agent / category task"}\n\n## fields\n- name\n- description\n- tools\n- model\n- memory scope\n\n## isolation\n- worktree | none`;
    case "subagentPlanner":
      return `# Subagent: Planner\n\n## role\n- 요구사항 해석 및 실행 계획 수립\n- 리스크/의존성 식별\n\n## inputs\n- 도메인: ${domain}\n- 목표: ${setting.title}\n\n## outputs\n- 단계별 작업 계획\n- 검증 체크리스트\n\n## handoff\n- implementer에게 작업 단위 전달`;
    case "subagentImplementer":
      return `# Subagent: Implementer\n\n## role\n- 코드/설정 변경 실제 수행\n- 실패 시 재시도 및 대안 경로 적용\n\n## inputs\n- Planner 산출 계획\n- workflow\n${workflowMd}\n\n## outputs\n- 변경 파일 목록\n- 적용 근거 및 영향 범위`;
    case "subagentReviewer":
      return `# Subagent: Reviewer\n\n## role\n- 변경 검증, 회귀 확인, 품질 게이트 점검\n\n## checklist\n- lint/type/build\n- smoke/deep smoke\n- 운영 리스크 점검\n\n## routing reference\n${routeMd}`;
    case "officialCategoryModel": {
      const official = setting.officialCategories;
      const categories = harnessType === "OpenCode" ? (official?.opencode ?? []) : (official?.claudecode ?? []);
      const source = harnessType === "OpenCode"
        ? "opencode 공식 configuration 문서"
        : "Anthropic Claude Code 공식 문서";
      const skillPathPrefix = harnessType === "OpenCode" ? ".opencode/skills" : ".claude/skills";
      const listMd = categories.length
        ? categories.map((c, i) => `- ${skillPathPrefix}/category-${String(i + 1).padStart(2, "0")}-${c.toLowerCase().replace(/[^a-z0-9가-힣]+/g, "-").replace(/^-+|-+$/g, "")}/SKILL.md`).join("\\n")
        : "- 카테고리 데이터 없음";
      return `<!-- 이 목록은 공식 skills 폴더에서 인식되는 추천 카테고리 파일 경로입니다. -->\n# Official Category Model (${harnessType})\n\n- source: ${source}\n- domain: ${domain}\n\n## recognized skill files\n${listMd}`;
    }
    case "outputStyles":
      return `# Output Styles\n\n- source: .claude/output-styles/*.md\n\n## style examples\n- teaching\n- explanatory\n- terse\n- custom-harness`;
    case "sandboxConfig":
      return `# Sandbox Configuration\n\n- source: settings.json.sandbox\n\n## filesystem\n- allowRead: [\"src/**\"]\n- denyRead: [\"secrets/**\"]\n\n## network\n- allowedDomains: [\"github.com\",\"docs.anthropic.com\"]`;
    case "modelConfig":
      return `# Model Configuration\n\n- source: settings.json.model\n\n## model\n${routeMd}\n\n## effort\n- low | medium | high | xhigh\n\n## alwaysThinking\n- false`;
    case "statusLine":
      return `# Status Line Customizer\n\n- source: settings.json.statusLine\n\n## render items\n- current branch\n- context usage\n- last smoke result\n- provider route`;
    case "worktreeInclude":
      return `# .worktreeinclude\n\n## include files\n- .env\n- .env.local\n- config/secrets.sample.json\n\n## purpose\n- worktree 생성 시 gitignored 필수 파일 복사`;

    default:
      return "";
  }
}

export default function RecommendationsPage() {
  const [settings, setSettings] = React.useState<RecommendedSetting[]>([]);
  const [loading, setLoading] = React.useState(true);
  const operationDomains: Domain[] = ["게임 클라이언트", "게임 서버", "프론트엔드", "백엔드"];
  const [activeDomain, setActiveDomain] = useState<Domain>(operationDomains[0]);
  const [clientEngine, setClientEngine] = useState<ClientEngine>("유니티");
  const [gameGenre, setGameGenre] = useState<GameGenre>("RPG");
  const [devLanguage, setDevLanguage] = useState<DevLanguage>("C#");
  const [status, setStatus] = useState("");
  const [note, setNote] = useState("");
  const [harnessType, setHarnessType] = useState<HarnessType>("OpenCode");
  const [activeView, setActiveView] = useState<HarnessView>("agents");
  const [selectedSubagentView, setSelectedSubagentView] = useState<
    Extract<HarnessView, "subagentPlanner" | "subagentImplementer" | "subagentReviewer">
  >("subagentPlanner");
  const [selectedSubagentLabel, setSelectedSubagentLabel] = useState("Subagent: Planner");
  const [readOnlyMode] = useState(true);

  React.useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      try {
        const data = await fetchRecommendedSettingsApi(
          activeDomain === "게임 클라이언트"
            ? {
                client_engine: clientEngine,
                game_genre: gameGenre,
                dev_language: devLanguage,
              }
            : undefined,
        );
        if (mounted) {
          setSettings(data);
        }
      } catch (e) {
        if (mounted) setStatus(`로드 실패: ${String(e)}`);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, [activeDomain, clientEngine, gameGenre, devLanguage]);

  const resolvedDomainForApi = useMemo<Domain>(() => {
    if (activeDomain !== "게임 클라이언트") return activeDomain;
    if (clientEngine === "유니티") return "Unity";
    if (clientEngine === "언리얼") return "Unreal";
    return "게임 클라이언트";
  }, [activeDomain, clientEngine]);

  const active = useMemo(
    () => settings.find((s) => s.domain === resolvedDomainForApi) ?? settings[0],
    [settings, resolvedDomainForApi],
  );

  const views: Array<{ key: HarnessView; label: string; visible: boolean }> = [
    { key: "openCodeJsonc", label: "opencode.jsonc", visible: harnessType === "OpenCode" },
    { key: "agents", label: harnessType === "OpenCode" ? ".opencode/AGENTS.md" : ".claude/CLAUDE.md", visible: true },
    { key: "rull", label: harnessType === "OpenCode" ? ".opencode/Rule.md" : ".claude/Rule.md", visible: true },
    { key: "commandsRegistry", label: harnessType === "OpenCode" ? ".opencode/commands/start-work.md" : ".claude/commands/start-work.md", visible: true },
    { key: "skill", label: harnessType === "OpenCode" ? ".opencode/skills/<name>/SKILL.md" : ".claude/skills/<name>/SKILL.md", visible: true },
    { key: "officialCategoryModel", label: harnessType === "OpenCode" ? ".opencode/skills/category-*/SKILL.md" : ".claude/skills/category-*/SKILL.md", visible: true },

    // OpenCode 공식 인식 항목 외 참조 뷰
    { key: "pluginHook", label: "Plugin", visible: false },
    { key: "pluginMcpList", label: "Plugin/MCP", visible: false },
    { key: "permissionsMatrix", label: "Permissions Matrix", visible: false },
    { key: "providerConfig", label: "Provider Config", visible: false },
    { key: "toolsRegistry", label: "Tools Registry", visible: false },
    { key: "formatterConfig", label: "Formatter Config", visible: false },
    { key: "watcherConfig", label: "Watcher", visible: false },
    { key: "serverConfig", label: "Server Config", visible: false },
    { key: "compactionConfig", label: "Compaction", visible: false },
    { key: "instructionsRegistry", label: "Instructions", visible: false },
    { key: "configPrecedence", label: "Config Precedence", visible: false },
    { key: "mcpOauthStatus", label: "MCP OAuth", visible: false },

    // Claude Code 공식 인식 항목
    { key: "claudeCodeJson", label: ".claude/settings.json", visible: harnessType === "ClaudeCode" },
    { key: "permissionModes", label: "Permission Modes", visible: false },
    { key: "hooksConfig", label: "Hooks Config", visible: false },
    { key: "autoMemory", label: "Auto Memory", visible: false },
    { key: "rulesManager", label: "Rules Manager", visible: false },

    // Subagent entries are rendered dynamically in the main button row (no separate list box)
    { key: "subagentsManager", label: "Subagents", visible: false },
    { key: "subagentPlanner", label: "Subagent: Planner", visible: false },
    { key: "subagentImplementer", label: "Subagent: Implementer", visible: false },
    { key: "subagentReviewer", label: "Subagent: Reviewer", visible: false },

    { key: "outputStyles", label: "Output Styles", visible: false },
    { key: "sandboxConfig", label: "Sandbox", visible: false },
    { key: "modelConfig", label: "Model Config", visible: false },
    { key: "statusLine", label: "Status Line", visible: false },
    { key: "worktreeInclude", label: ".worktreeinclude", visible: false },
  ];

  const visibleViews = views.filter((v) => v.visible);
  const subagentViews = useMemo(() => {
    const candidates = active?.subagentCandidates ?? ["Planner", "Implementer", "Reviewer"];
    const mapped = candidates.map((name) => {
      const lowered = name.toLowerCase();
      if (lowered.includes("plan")) {
        return { key: "subagentPlanner" as const, label: `Subagent: ${name}` };
      }
      if (lowered.includes("implement") || lowered.includes("release") || lowered.includes("operator")) {
        return { key: "subagentImplementer" as const, label: `Subagent: ${name}` };
      }
      return { key: "subagentReviewer" as const, label: `Subagent: ${name}` };
    });

    const unique: Array<{ key: Extract<HarnessView, "subagentPlanner" | "subagentImplementer" | "subagentReviewer">; label: string }> = [];
    for (const item of mapped) {
      if (!unique.some((u) => u.label === item.label)) {
        unique.push(item);
      }
    }
    return unique;
  }, [active]);

  const activeSubagentSelection = useMemo(() => {
    const current = subagentViews.find((v) => v.key === selectedSubagentView && v.label === selectedSubagentLabel);
    return current ?? subagentViews[0] ?? null;
  }, [subagentViews, selectedSubagentView, selectedSubagentLabel]);

  const effectiveView: HarnessView =
    activeView === "subagentPlanner" || activeView === "subagentImplementer" || activeView === "subagentReviewer"
      ? activeView
      : activeView === "subagentsManager"
        ? (activeSubagentSelection?.key ?? selectedSubagentView)
        : activeView;

  const renderedContent = useMemo(
    () => renderViewContent(effectiveView, harnessType, active),
    [effectiveView, harnessType, active],
  );

  const selectableViews = useMemo(
    () => [
      ...visibleViews.map((view) => ({
        value: `${view.key}||${view.label}`,
        key: view.key,
        label: view.label,
        isSubagent: false,
      })),
      ...subagentViews.map((view) => ({
        value: `${view.key}||${view.label}`,
        key: view.key,
        label: view.label,
        isSubagent: true,
      })),
    ],
    [visibleViews, subagentViews],
  );

  const activeSelectValue = useMemo(() => {
    if (activeView === "subagentPlanner" || activeView === "subagentImplementer" || activeView === "subagentReviewer") {
      const fallbackLabel = activeSubagentSelection?.label ?? selectedSubagentLabel;
      return `${activeView}||${fallbackLabel}`;
    }
    const selected = visibleViews.find((view) => view.key === activeView);
    return selected ? `${selected.key}||${selected.label}` : "";
  }, [activeView, activeSubagentSelection, selectedSubagentLabel, visibleViews]);

  const activeViewLabel = useMemo(() => {
    if (activeView === "subagentPlanner" || activeView === "subagentImplementer" || activeView === "subagentReviewer") {
      return activeSubagentSelection?.label ?? selectedSubagentLabel;
    }
    if (activeView === "subagentsManager") {
      return `Subagents / ${activeSubagentSelection?.label ?? selectedSubagentLabel}`;
    }
    return visibleViews.find((v) => v.key === activeView)?.label ?? activeView;
  }, [visibleViews, activeView, activeSubagentSelection, selectedSubagentLabel]);

  const handleDownloadZip = async () => {
    if (!active) return;
    setStatus("템플릿 ZIP 생성 중...");
    try {
      const blob = await downloadTemplateApi(resolvedDomainForApi, {
        harnessType,
        modelRouting: active.modelRouting,
        workflow: active.workflow,
        mcp: active.mcp,
        rules: active.rules,
        reason: active.reason,
        subagentCandidates: active.subagentCandidates,
        dynamicViews: active.dynamicViews,
        officialCategories: active.officialCategories,
      });
      downloadBlob(blob, `${toSlug(active.domain)}-${harnessType.toLowerCase()}-ops-template.zip`);
      setStatus("ZIP 다운로드 완료");
    } catch (e) {
      setStatus(`ZIP 생성 실패: ${String(e)}`);
    }
  };

  const handleCloneScript = async () => {
    if (!active) return;
    setStatus("클론 스크립트 생성 중...");
    try {
      const data = await getCloneInstructionsApi(resolvedDomainForApi);
      await navigator.clipboard.writeText(data.script);
      setStatus("clone.sh 스크립트를 클립보드에 복사했습니다.");
    } catch (e) {
      setStatus(`클론 스크립트 생성 실패: ${String(e)}`);
    }
  };

  const handleFeedback = async (rating: number) => {
    if (!active) return;
    setStatus("피드백 저장 중...");
    try {
      const contextNote =
        activeDomain === "게임 클라이언트"
          ? `[게임클라 선택] 엔진=${clientEngine}, 장르=${gameGenre}, 언어=${devLanguage}${note ? ` | note=${note}` : ""}`
          : note;

      await sendRecommendationFeedbackApi({
        domain: resolvedDomainForApi,
        rating,
        note: contextNote,
        chosen_models: active.modelRouting,
        chosen_workflow: active.workflow,
      });
      setStatus("피드백 저장 완료 (지속 학습 반영)");
      const refreshed = await fetchRecommendedSettingsApi(
        activeDomain === "게임 클라이언트"
          ? {
              client_engine: clientEngine,
              game_genre: gameGenre,
              dev_language: devLanguage,
            }
          : undefined,
      );
      setSettings(refreshed);
      setNote("");
    } catch (e) {
      setStatus(`피드백 저장 실패: ${String(e)}`);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
          <div>
            <h1 className="text-2xl font-bold">하네스 운영 추천 셋팅</h1>
            <p className="text-sm text-slate-600">도메인별 운영 지침과 셋팅 타입별 산출물을 리스트로 제공합니다.</p>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/settings">
              <Button variant="outline">프로젝트 설정 보기</Button>
            </Link>
            <Link href="/">
              <Button variant="outline">보드로 돌아가기</Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-4 px-4 py-6">
        {loading ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-slate-500">
            추천 셋팅 데이터를 불러오는 중...
          </div>
        ) : (
          <>
            <section className="grid gap-3 lg:grid-cols-[260px_1fr]">
              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <div className="mb-2 text-sm font-semibold text-slate-700">도메인 리스트 박스</div>
                <div className="space-y-2">
                  {operationDomains.map((domain) => {
                    const selected = domain === activeDomain;
                    return (
                      <button
                        key={domain}
                        type="button"
                        onClick={() => setActiveDomain(domain)}
                        className={`w-full rounded-xl border px-3 py-2 text-left text-sm transition ${
                          selected
                            ? "border-blue-500 bg-blue-50 text-blue-700"
                            : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                        }`}
                      >
                        {domain}
                      </button>
                    );
                  })}
                </div>

                {activeDomain === "게임 클라이언트" && (
                  <div className="mt-4 space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <div className="text-xs font-semibold text-slate-700">게임 클라이언트 세부 선택</div>

                    <label className="block text-xs text-slate-600">
                      <span className="mb-1 block">엔진</span>
                      <select
                        value={clientEngine}
                        onChange={(e) => setClientEngine(e.target.value as ClientEngine)}
                        className="w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-800"
                      >
                        <option value="유니티">유니티</option>
                        <option value="언리얼">언리얼</option>
                        <option value="자체엔진">자체엔진</option>
                      </select>
                    </label>

                    <label className="block text-xs text-slate-600">
                      <span className="mb-1 block">게임 개발 장르</span>
                      <select
                        value={gameGenre}
                        onChange={(e) => setGameGenre(e.target.value as GameGenre)}
                        className="w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-800"
                      >
                        <option value="RPG">RPG</option>
                        <option value="FPS/TPS">FPS/TPS</option>
                        <option value="전략/시뮬레이션">전략/시뮬레이션</option>
                        <option value="캐주얼/하이퍼캐주얼">캐주얼/하이퍼캐주얼</option>
                        <option value="스포츠/레이싱">스포츠/레이싱</option>
                        <option value="퍼즐">퍼즐</option>
                        <option value="MMO">MMO</option>
                        <option value="액션/어드벤처">액션/어드벤처</option>
                        <option value="기타">기타</option>
                      </select>
                    </label>

                    <label className="block text-xs text-slate-600">
                      <span className="mb-1 block">개발 언어</span>
                      <select
                        value={devLanguage}
                        onChange={(e) => setDevLanguage(e.target.value as DevLanguage)}
                        className="w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-800"
                      >
                        <option value="C#">C#</option>
                        <option value="C++">C++</option>
                        <option value="Blueprint">Blueprint</option>
                        <option value="Lua">Lua</option>
                        <option value="TypeScript">TypeScript</option>
                        <option value="Rust">Rust</option>
                        <option value="Python">Python</option>
                        <option value="기타">기타</option>
                      </select>
                    </label>

                    <div className="rounded-md border border-blue-200 bg-blue-50 px-2 py-1.5 text-[11px] text-blue-700">
                      실제 추천/템플릿 조회 도메인: <span className="font-semibold">{resolvedDomainForApi}</span>
                    </div>
                  </div>
                )}
              </div>

              <div className="space-y-3">
                <div className="rounded-2xl border border-slate-200 bg-white p-4">
                  <div className="mb-2 text-sm font-semibold text-slate-700">셋팅 타입</div>
                  <div className="flex flex-wrap gap-2">
                    {(["OpenCode", "ClaudeCode"] as HarnessType[]).map((type) => (
                      <Button
                        key={type}
                        type="button"
                        variant={harnessType === type ? "default" : "outline"}
                        onClick={() => {
                          setHarnessType(type);
                          if (type === "OpenCode" && activeView === "claudeCodeJson") {
                            setActiveView("openCodeJsonc");
                          }
                          if (type === "ClaudeCode" && activeView === "openCodeJsonc") {
                            setActiveView("claudeCodeJson");
                          }
                        }}
                      >
                        {type}
                      </Button>
                    ))}
                  </div>
                </div>

                <RecommendedSettingCard
                  settings={settings}
                  activeSetting={resolvedDomainForApi}
                />
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="mb-3 flex items-center justify-between gap-2">
                <div className="text-sm font-semibold text-slate-700">하네스 운영 추천 셋팅 리스트</div>
                <div className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-600">
                  {readOnlyMode ? "Read-only" : "Editable"}
                </div>
              </div>
              <p className="mb-3 rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-xs leading-relaxed text-blue-800">
                이 영역은 <span className="font-semibold">.opencode / .claude</span>에 실제로 배치될 운영 파일을 미리 확인하는 리스트입니다.
                도메인/엔진/장르/언어 조합에 따라 추천 규칙과 스킬 구성이 달라지며, 선택한 항목은 복사하거나 ZIP으로 바로 내려받아 팀 운영 템플릿으로 사용할 수 있습니다.
              </p>
              <div className="mb-3">
                <label className="block text-xs text-slate-600">
                  <span className="mb-1 block">파일/산출물 리스트박스</span>
                  <select
                    value={activeSelectValue}
                    onChange={(e) => {
                      const selected = selectableViews.find((view) => view.value === e.target.value);
                      if (!selected) return;
                      if (selected.isSubagent) {
                        setActiveView(selected.key as Extract<HarnessView, "subagentPlanner" | "subagentImplementer" | "subagentReviewer">);
                        setSelectedSubagentView(selected.key as Extract<HarnessView, "subagentPlanner" | "subagentImplementer" | "subagentReviewer">);
                        setSelectedSubagentLabel(selected.label);
                        return;
                      }
                      setActiveView(selected.key);
                    }}
                    size={Math.min(12, Math.max(6, selectableViews.length))}
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800"
                  >
                    {selectableViews.map((view) => (
                      <option key={view.value} value={view.value}>
                        {view.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-slate-600">
                <span>선택 리스트: <span className="font-semibold text-slate-800">{activeViewLabel}</span></span>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(renderedContent || "");
                      setStatus(`${activeViewLabel} 내용을 클립보드에 복사했습니다.`);
                    } catch (e) {
                      setStatus(`복사 실패: ${String(e)}`);
                    }
                  }}
                >
                  복사
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={handleDownloadZip}
                >
                  다운로드
                </Button>
              </div>
              <pre className="max-h-[460px] overflow-auto rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed text-slate-800">
                {renderedContent || "선택된 산출물 데이터가 없습니다."}
              </pre>
            </section>

            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="mb-3 text-sm font-semibold text-slate-700">운영 액션</div>
              <div className="flex flex-wrap gap-2">
                <Button onClick={handleDownloadZip}>템플릿 ZIP 다운로드</Button>
                <Button variant="outline" onClick={handleCloneScript}>클론 스크립트 복사</Button>
                <Button variant="outline" onClick={() => handleFeedback(5)} disabled={readOnlyMode}>추천 좋음(5점)</Button>
                <Button variant="outline" onClick={() => handleFeedback(3)} disabled={readOnlyMode}>보통(3점)</Button>
                <Button variant="outline" onClick={() => handleFeedback(1)} disabled={readOnlyMode}>개선 필요(1점)</Button>
              </div>
              <textarea
                className="mt-3 w-full rounded-xl border border-slate-200 p-3 text-sm"
                rows={3}
                placeholder={readOnlyMode ? "읽기 전용 모드에서는 코멘트 편집이 비활성화됩니다." : "추천 품질 개선에 도움이 되는 코멘트를 남겨주세요."}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                readOnly={readOnlyMode}
              />
              {active && (
                <div className="mt-2 text-xs text-slate-500">
                  도메인: {active.domain} / 근거 데이터: {active.evidenceCount ?? 0}건 / 피드백: {active.feedbackCount ?? 0}건
                </div>
              )}
              {status && <div className="mt-2 text-sm text-blue-700">{status}</div>}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
