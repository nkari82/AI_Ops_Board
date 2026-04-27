"use client";
import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  BookOpen,
  Bot,
  CheckCircle2,
  Code2,
  Cpu,
  Database,
  Flame,
  Gamepad2,
  GitBranch,
  Globe2,
  Layers3,
  Network,
  RefreshCw,
  Search,
  Server,
  Settings2,
  ShieldAlert,
  Sparkles,
  TerminalSquare,
  UserRound,
  Wrench,
  Zap,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

// ============================================================
// AI OPS BOARD - PRODUCTION FRONTEND PROTOTYPE
// ============================================================
// Data policy:
// - User Board: manual user input only. No crawling, no AI synthesis.
// - All other boards: web crawling + AI summary + accumulation + synthetic data.
//
// Main concepts:
// - 추천 셋팅: domain-specific recommended AI operation setup.
// - 실전 운용: rules + skills + AGENTS.md/CLAUDE.md patterns merged together.
// - LLM Router: free/local models for cheap work, paid models for high-value reasoning.
// ============================================================

type Domain =
  | "게임 클라이언트"
  | "게임 서버"
  | "프론트엔드"
  | "백엔드"
  | "Unity"
  | "Unreal"
  | "로컬 LLM"
  | "Agent/MCP";

type BoardCategory =
  | "실전 운용"
  | "아키텍처"
  | "실전 사례"
  | "깨알팁"
  | "주의/함정"
  | "플러그인/MCP";

type SourceKind =
  | "crawled"
  | "ai_summarized"
  | "accumulated"
  | "ai_synthesized"
  | "manual_user_input";

type OperationPost = {
  id: number;
  title: string;
  category: BoardCategory;
  domain: Domain;
  score: number;
  sourceKind: Exclude<SourceKind, "manual_user_input">;
  sources: string[];
  updatedAt: string;
  summary: string;
  rule?: string;
  skill?: string;
  agentRule?: string;
  badExample?: string;
  goodExample?: string;
  action: string;
  tags: string[];
  risk: "low" | "medium" | "high";
};

type UserPost = {
  id: number;
  title: string;
  body: string;
  author: string;
  domain: Domain;
  votes: number;
  createdAt: string;
  tags: string[];
  sourceKind: "manual_user_input";
};

type LlmModel = {
  id: string;
  name: string;
  provider: "Local" | "Groq" | "Google AI Studio" | "OpenRouter" | "Claude" | "OpenAI";
  cost: "free" | "cheap" | "paid";
  role: string;
  endpoint: string;
  enabled: boolean;
};

type RecommendedSetting = {
  domain: Domain;
  title: string;
  score: number;
  modelRouting: string[];
  workflow: string[];
  mcp: string[];
  rules: string[];
  reason: string;
};

const domains: Domain[] = [
  "게임 클라이언트",
  "게임 서버",
  "프론트엔드",
  "백엔드",
  "Unity",
  "Unreal",
  "로컬 LLM",
  "Agent/MCP",
];

const categories: BoardCategory[] = [
  "실전 운용",
  "아키텍처",
  "실전 사례",
  "깨알팁",
  "주의/함정",
  "플러그인/MCP",
];

const operationPosts: OperationPost[] = [
  {
    id: 1,
    title: "Claude Code는 diff-only 리뷰어로 제한",
    category: "실전 운용",
    domain: "백엔드",
    score: 98,
    sourceKind: "ai_synthesized",
    sources: ["Reddit", "Claude Docs", "Blog"],
    updatedAt: "09:00",
    summary:
      "크롤링된 사례와 커뮤니티 패턴을 합성한 결과, Claude Code를 탐색용으로 쓰는 순간 토큰 비용이 커진다. OpenCode/로컬 모델로 후보 파일을 좁히고 Claude는 diff 리뷰에 집중시키는 구조가 가장 안정적이다.",
    rule: "전체 프로젝트 스캔 금지",
    skill: "diff 기반 리뷰",
    agentRule: "Review only the provided diff. Do not inspect unrelated files unless required.",
    badExample: "이 프로젝트 전체를 읽고 리뷰해줘.",
    goodExample: "이 diff만 정확성, 성능, 보안 관점으로 리뷰해줘.",
    action: "CLAUDE.md에 diff-only review 규칙을 추가한다.",
    tags: ["Claude Code", "토큰 절약", "diff-review"],
    risk: "low",
  },
  {
    id: 2,
    title: "Unity 런타임 코드는 GC 0 규칙을 기본 적용",
    category: "실전 운용",
    domain: "Unity",
    score: 97,
    sourceKind: "accumulated",
    sources: ["Reddit", "GitHub Issues", "Unity Blog"],
    updatedAt: "10:20",
    summary:
      "Unity/게임 클라이언트 사례를 축적해 만든 운용 규칙. AI가 편의성 코드를 넣어 Update 계열 hot path에 할당을 만들지 않도록 AGENTS.md에서 강하게 제한한다.",
    rule: "Update/LateUpdate/FixedUpdate hot path에서 LINQ, reflection, 임시 컬렉션 금지",
    skill: "Profiler 로그 요약 후 diff 리뷰",
    agentRule: "Avoid GC allocations in runtime hot paths. Do not use LINQ in Update-like paths.",
    badExample: "동작만 맞추는 LINQ 기반 코드 생성",
    goodExample: "캐시된 컬렉션과 명시적 루프로 할당 없는 구현",
    action: "Unity 추천 셋팅에 GC 0 규칙을 기본 포함한다.",
    tags: ["Unity", "GC", "AGENTS.md", "performance"],
    risk: "medium",
  },
  {
    id: 3,
    title: "MCP는 권한을 작게 나눠 붙여야 안전",
    category: "플러그인/MCP",
    domain: "Agent/MCP",
    score: 94,
    sourceKind: "ai_summarized",
    sources: ["MCP Docs", "Security Blog", "GitHub"],
    updatedAt: "13:00",
    summary:
      "Filesystem/Shell 계열 MCP는 생산성을 높이지만 권한이 크다. 프로젝트별 scope, read-only, command allowlist를 적용하지 않으면 에이전트 실수가 실제 파일 파괴나 RCE 위험으로 이어질 수 있다.",
    rule: "unrestricted filesystem/shell MCP 금지",
    skill: "MCP 권한 분리 및 위험도 라벨링",
    agentRule: "Use scoped tools only. Never run destructive shell commands without explicit approval.",
    badExample: "전체 디스크 접근 + unrestricted shell MCP",
    goodExample: "프로젝트 폴더 read-only filesystem + 허용 명령 allowlist",
    action: "MCP 추천 카드에 위험도와 권한 범위를 함께 표시한다.",
    tags: ["MCP", "security", "filesystem", "shell"],
    risk: "high",
  },
  {
    id: 4,
    title: "게임 서버 AI 리뷰는 동시성/트랜잭션 중심으로 분리",
    category: "아키텍처",
    domain: "게임 서버",
    score: 92,
    sourceKind: "ai_synthesized",
    sources: ["HN", "Backend Blog", "Reddit"],
    updatedAt: "18:00",
    summary:
      "게임 서버는 일반 CRUD보다 race condition, idempotency, retry, transaction 경계가 중요하다. AI 리뷰 체크리스트도 일반 백엔드와 분리해야 한다.",
    rule: "API 변경 시 동시성/트랜잭션/재시도 정책 확인",
    skill: "장애 로그 요약 후 원인 후보 압축",
    agentRule: "Review concurrency, transaction boundaries, idempotency, retry, and timeout behavior.",
    action: "게임 서버 추천 셋팅에 Redis/PostgreSQL MCP와 장애 로그 요약 루틴을 포함한다.",
    tags: ["game-server", "concurrency", "DB", "review"],
    risk: "medium",
  },
  {
    id: 5,
    title: "로그 2,000줄 대신 실패 명령 + 첫 에러 + 마지막 에러만 전달",
    category: "깨알팁",
    domain: "백엔드",
    score: 88,
    sourceKind: "accumulated",
    sources: ["Reddit", "User Pattern", "Build Logs"],
    updatedAt: "22:00",
    summary:
      "장기 프로젝트에서 실패 로그 전체를 LLM에 넣으면 토큰 낭비와 오판이 생긴다. 실패 명령, 첫 에러, 마지막 에러, 관련 파일 경로만 요약해서 전달하는 것이 더 정확하다.",
    rule: "긴 로그 원문 전달 금지",
    skill: "로그 압축 템플릿 사용",
    agentRule: "Summarize logs before reasoning. Keep command, first error, last error, and relevant file paths.",
    action: "실전 운용 템플릿에 로그 요약 프롬프트를 추가한다.",
    tags: ["logs", "debugging", "token-saving"],
    risk: "low",
  },
];

const userPosts: UserPost[] = [
  {
    id: 101,
    title: "3090 2장으로 로컬 LLM 탐색 모델 돌리는 팁",
    body: "Qwen 계열을 OpenCode 탐색/요약용으로 쓰고 Claude는 최종 리뷰만 쓰는 구성이 제일 안정적이었다.",
    author: "dev01",
    domain: "로컬 LLM",
    votes: 21,
    createdAt: "오늘 11:30",
    tags: ["3090", "Qwen", "OpenCode"],
    sourceKind: "manual_user_input",
  },
  {
    id: 102,
    title: "Unity 프로젝트에서 AGENTS.md 짧게 줄인 후기",
    body: "규칙을 영어 1줄 + 한국어 설명 1줄로 줄였더니 반복 설명이 줄고 결과가 더 안정적이었다.",
    author: "client-dev",
    domain: "Unity",
    votes: 14,
    createdAt: "어제 22:10",
    tags: ["Unity", "AGENTS.md", "GC"],
    sourceKind: "manual_user_input",
  },
];

const models: LlmModel[] = [
  {
    id: "local-qwen",
    name: "Local Qwen Coder",
    provider: "Local",
    cost: "free",
    role: "파일 탐색, 로그 요약, 간단 수정",
    endpoint: "http://localhost:8000/v1",
    enabled: true,
  },
  {
    id: "groq-free",
    name: "Groq Free Tier",
    provider: "Groq",
    cost: "free",
    role: "빠른 요약, 분류, 초안 생성",
    endpoint: "https://api.groq.com/openai/v1",
    enabled: true,
  },
  {
    id: "google-free",
    name: "Google AI Studio Free",
    provider: "Google AI Studio",
    cost: "free",
    role: "긴 문서 요약, 일반 분류",
    endpoint: "https://generativelanguage.googleapis.com",
    enabled: true,
  },
  {
    id: "openrouter-free",
    name: "OpenRouter Free Models",
    provider: "OpenRouter",
    cost: "free",
    role: "무료 공개 모델 실험",
    endpoint: "https://openrouter.ai/api/v1",
    enabled: false,
  },
  {
    id: "claude",
    name: "Claude Premium",
    provider: "Claude",
    cost: "paid",
    role: "아키텍처 판단, 보안/성능 리뷰, 최종 diff 리뷰",
    endpoint: "https://api.anthropic.com",
    enabled: true,
  },
];

const recommendedSettings: RecommendedSetting[] = [
  {
    domain: "게임 클라이언트",
    title: "OpenCode 탐색 + Claude 성능 리뷰 + 엔진 hot path 규칙",
    score: 96,
    modelRouting: ["로컬 모델: 파일 탐색/로그 요약", "Claude: 성능/구조 판단", "무료 API: 글 요약/분류"],
    workflow: ["OpenCode로 관련 파일 후보 압축", "작은 diff 구현", "엔진 로그 요약", "Claude로 성능 리뷰"],
    mcp: ["Scoped Filesystem", "GitHub", "엔진 로그 파서"],
    rules: ["전체 스캔 금지", "diff-only review", "런타임 hot path 할당 금지"],
    reason: "게임 클라이언트는 반복 속도와 런타임 성능을 같이 잡아야 하므로 역할 분리가 핵심이다.",
  },
  {
    domain: "게임 서버",
    title: "동시성/트랜잭션 리뷰 + 장애 로그 요약 루틴",
    score: 94,
    modelRouting: ["로컬 모델: 로그 압축", "Claude: race/transaction 리뷰", "무료 모델: 테스트 초안"],
    workflow: ["변경 API 영향 범위 추출", "테스트 작성", "장애 로그 요약", "Claude로 동시성 리뷰"],
    mcp: ["PostgreSQL", "Redis", "GitHub", "Slack 알림"],
    rules: ["idempotency 확인", "retry/timeout 명시", "migration 리뷰 필수"],
    reason: "게임 서버는 장애 비용이 크므로 기능보다 안정성 리뷰를 우선해야 한다.",
  },
  {
    domain: "Unity",
    title: "GC 0 규칙 고정 + Update 경로 집중 리뷰",
    score: 98,
    modelRouting: ["로컬 모델: MonoBehaviour 탐색", "Claude: hot path 리뷰", "무료 모델: 로그 요약"],
    workflow: ["관련 스크립트만 탐색", "할당 없는 구현", "Profiler/로그 확인", "Claude로 diff 리뷰"],
    mcp: ["Scoped Filesystem", "Git", "Unity Log Parser"],
    rules: ["LINQ 금지", "reflection 금지", "Update 임시 컬렉션 금지"],
    reason: "Unity는 AI가 편한 코드를 만들수록 GC 문제가 생기기 쉬워 규칙 파일 효과가 크다.",
  },
  {
    domain: "Unreal",
    title: "C++ ownership 리뷰 + 빌드 로그 압축",
    score: 93,
    modelRouting: ["로컬 모델: 빌드 로그 요약", "Claude: lifetime/ownership 리뷰", "무료 모델: 문서 요약"],
    workflow: ["빌드 로그 압축", "관련 클래스/모듈만 탐색", "RAII 중심 수정", "Claude로 lifetime 리뷰"],
    mcp: ["Scoped Filesystem", "GitHub", "Build Log Parser"],
    rules: ["ownership 명시", "hidden allocation 확인", "unrelated refactor 금지"],
    reason: "Unreal은 C++ lifetime과 빌드 로그를 잘 압축하는 것이 비용과 시간을 줄인다.",
  },
];

const agentsTemplate = `# AGENTS.md

## Goal
Minimize token usage while maintaining implementation quality.
# 목표: 토큰 사용을 최소화하면서 구현 품질 유지

## Core Rules
- Do not scan the whole repository unless explicitly requested.
# 요청 없이는 전체 프로젝트를 스캔하지 않는다.

- Identify the smallest relevant file set first.
# 먼저 가장 작은 관련 파일 집합을 찾는다.

- Prefer minimal safe diffs.
# 안전한 최소 변경을 우선한다.

- Do not refactor unrelated code.
# 관련 없는 코드는 리팩토링하지 않는다.

- Do not add TODO comments instead of implementation.
# TODO 주석으로 대체하지 말고 실제 구현한다.

## Workflow
1. Explore without edits.
2. Plan minimal changes.
3. Implement small diffs.
4. Validate cheaply first.

## Model Routing
Cheap/local model: search, summarize, logs, simple edits.
Strong/cloud model: architecture, difficult bugs, security, final review.`;

function cn(...items: Array<string | false | undefined>) {
  return items.filter(Boolean).join(" ");
}

function riskClass(risk: OperationPost["risk"]) {
  if (risk === "high") return "border-red-200 bg-red-50 text-red-700";
  if (risk === "medium") return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-emerald-200 bg-emerald-50 text-emerald-700";
}

function sourceLabel(kind: SourceKind) {
  switch (kind) {
    case "manual_user_input":
      return "수동 입력";
    case "crawled":
      return "웹 크롤링";
    case "ai_summarized":
      return "AI 요약";
    case "accumulated":
      return "축적 데이터";
    case "ai_synthesized":
      return "AI 합성";
  }
}

function domainIcon(domain: Domain) {
  switch (domain) {
    case "게임 클라이언트":
      return <Gamepad2 className="h-4 w-4" />;
    case "게임 서버":
      return <Server className="h-4 w-4" />;
    case "프론트엔드":
      return <Code2 className="h-4 w-4" />;
    case "백엔드":
      return <Database className="h-4 w-4" />;
    case "Unity":
      return <Cpu className="h-4 w-4" />;
    case "Unreal":
      return <TerminalSquare className="h-4 w-4" />;
    case "로컬 LLM":
      return <Bot className="h-4 w-4" />;
    case "Agent/MCP":
      return <Network className="h-4 w-4" />;
  }
}

export default function AiOpsBoard() {
  const [query, setQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<BoardCategory | "전체">("전체");
  const [selectedDomain, setSelectedDomain] = useState<Domain | "전체">("전체");
  const [selectedModel, setSelectedModel] = useState(models[0].id);
  const [activeSetting, setActiveSetting] = useState<Domain>("Unity");
  const [draftTitle, setDraftTitle] = useState("");
  const [template, setTemplate] = useState("");
  const [generating, setGenerating] = useState(false);

  const generateOpsTemplate = async (domain: string) => {
    setGenerating(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8005";
      const response = await fetch(`${apiUrl}/api/templates/generate?domain=${domain}`, { method: "POST" });
      const data = await response.json();
      setTemplate(data.template);
    } catch (e) {
      console.error("Template generation failed:", e);
    } finally {
      setGenerating(false);
    }
  };

  // ... (existing state)

  // API 호출 추가
  const fetchKnowledge = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8005";
      const response = await fetch(`${apiUrl}/api/knowledge`);
      const data = await response.json();
      setKnowledgeCards(data);
    } catch (e) {
      console.error("Knowledge fetch failed:", e);
    }
  };

  React.useEffect(() => {
    fetchKnowledge();
  }, []);
  const [crawlResults, setCrawlResults] = useState<{
    reddit?: any[];
    github?: any[];
    hn?: any[];
  }>({});

  const filteredPosts = useMemo(() => {
    const q = query.trim().toLowerCase();
    return operationPosts.filter((post) => {
      const categoryOk = selectedCategory === "전체" || post.category === selectedCategory;
      const domainOk = selectedDomain === "전체" || post.domain === selectedDomain;
      const queryOk =
        q.length === 0 ||
        [post.title, post.summary, post.rule, post.skill, post.agentRule, post.domain, post.category, ...post.tags]
          .filter(Boolean)
          .join(" ")
          .toLowerCase()
          .includes(q);
      return categoryOk && domainOk && queryOk;
    });
  }, [query, selectedCategory, selectedDomain]);

  const model = models.find((item) => item.id === selectedModel) ?? models[0];
  const setting = recommendedSettings.find((item) => item.domain === activeSetting) ?? recommendedSettings[0];

  const testCrawl = async () => {
    if (crawling) return;
    setCrawling(true);
    setCrawlResults({});
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8005";
      const [reddit, github, hn] = await Promise.all([
        fetch(`${apiUrl}/api/crawl/reddit`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ subreddit: "LocalLLaMA", limit: 5 }),
        }).then((r) => r.json()),
        fetch(`${apiUrl}/api/crawl/github?limit=5`, { method: "POST" }).then((r) => r.json()),
        fetch(`${apiUrl}/api/crawl/hn?limit=5`, { method: "POST" }).then((r) => r.json()),
      ]);
      setCrawlResults({ reddit, github, hn });
    } catch (e) {
      console.error("Crawl test failed:", e);
    } finally {
      setCrawling(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-blue-600">
              <Sparkles className="h-4 w-4" /> AI 운용 지식을 자동 수집·요약·축적·합성하는 보드
            </div>
            <h1 className="mt-1 text-2xl font-bold tracking-tight md:text-3xl">AI Ops Board</h1>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
            <Button
              size="sm"
              variant={crawling ? "secondary" : "default"}
              onClick={testCrawl}
              disabled={crawling}
            >
              <RefreshCw className={`h-3.5 w-3.5 mr-1 ${crawling ? "animate-spin" : ""}`} />
              {crawling ? "크롤링 중..." : "크롤링 테스트"}
            </Button>
            <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-3 py-1">
              <Flame className="h-3.5 w-3.5" /> 추천 셋팅 하루 1회
            </span>
          </div>
        </div>
      </header>

      {Object.keys(crawlResults).length > 0 && (
        <div className="mx-auto max-w-7xl px-4 py-4">
          <Card className="rounded-2xl border-slate-200">
            <CardContent className="p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" /> 크롤링 결과
              </div>
              <div className="grid gap-4 md:grid-cols-3">
                {crawlResults.reddit && (
                  <div>
                    <div className="mb-2 text-xs font-medium text-slate-500">Reddit</div>
                    <div className="space-y-1">
                      {crawlResults.reddit.map((r, i) => (
                        <div key={i} className="truncate text-sm">{r.title}</div>
                      ))}
                    </div>
                  </div>
                )}
                {/* 지식 카드 뷰 */}
                {knowledgeCards.length > 0 && (
                  <div>
                    <div className="mb-2 text-xs font-medium text-slate-500">AI 지식 카드</div>
                    <div className="space-y-1">
                      {knowledgeCards.map((card, i) => (
                        <div key={i} className="truncate text-sm font-bold text-blue-700">{card.title}</div>
                      ))}
                    </div>
                  </div>
                )}
                {crawlResults.github && (
                  <div>
                    <div className="mb-2 text-xs font-medium text-slate-500">GitHub</div>
                    <div className="space-y-1">
                      {crawlResults.github.map((r, i) => (
                        <div key={i} className="truncate text-sm">{r.name}</div>
                      ))}
                    </div>
                  </div>
                )}
                {crawlResults.hn && (
                  <div>
                    <div className="mb-2 text-xs font-medium text-slate-500">Hacker News</div>
                    <div className="space-y-1">
                      {crawlResults.hn.map((r, i) => (
                        <div key={i} className="truncate text-sm">{r.title}</div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6">
        <section className="grid gap-4 lg:grid-cols-[1.25fr_0.75fr]">
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
            <Card className="overflow-hidden rounded-3xl border-blue-100 bg-gradient-to-br from-blue-950 via-slate-900 to-slate-950 text-white shadow-xl">
              <CardContent className="p-6 md:p-8">
                <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                  <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-sm text-blue-100 ring-1 ring-white/15">
                    <Flame className="h-4 w-4" /> 추천 셋팅
                  </div>
                  <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-sm font-bold text-emerald-700">
                    {setting.score}
                  </span>
                </div>

                <div className="flex flex-wrap gap-2">
                  {recommendedSettings.map((item) => (
                    <button
                      key={item.domain}
                      onClick={() => setActiveSetting(item.domain)}
                      className={cn(
                        "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm transition",
                        activeSetting === item.domain
                          ? "bg-white text-slate-950"
                          : "bg-white/10 text-slate-200 hover:bg-white/15"
                      )}
                    >
                      {domainIcon(item.domain)} {item.domain}
                    </button>
                  ))}
                </div>

                <div className="mt-7 grid gap-6 md:grid-cols-[0.9fr_1.1fr]">
                  <div>
                    <h2 className="text-2xl font-bold leading-tight md:text-3xl">{setting.title}</h2>
                    <p className="mt-3 text-sm leading-6 text-slate-300">{setting.reason}</p>
                  </div>
                  <div className="grid gap-3">
                    <InfoBlock title="Model Routing" icon={<Bot className="h-4 w-4" />} items={setting.modelRouting} dark />
                    <InfoBlock title="Workflow" icon={<GitBranch className="h-4 w-4" />} items={setting.workflow} dark />
                    <InfoBlock title="MCP / Plugins" icon={<Network className="h-4 w-4" />} items={setting.mcp} dark />
                    <InfoBlock title="Rules" icon={<Wrench className="h-4 w-4" />} items={setting.rules} dark />
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
            <CardContent className="p-5">
              <h2 className="flex items-center gap-2 text-lg font-bold">
                <Bot className="h-5 w-5 text-blue-600" /> LLM Router
              </h2>
              <p className="mt-1 text-sm leading-6 text-slate-600">
                무료/로컬 모델은 탐색·요약·분류, 유료 모델은 고급 판단·리뷰에만 사용한다.
              </p>
              <div className="mt-4 grid gap-2">
                {models.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => setSelectedModel(item.id)}
                    className={cn(
                      "rounded-2xl border p-3 text-left transition",
                      selectedModel === item.id
                        ? "border-slate-950 bg-slate-950 text-white"
                        : "border-slate-200 bg-slate-50 hover:bg-slate-100"
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="font-semibold">{item.name}</div>
                      <span className={cn("rounded-full px-2 py-0.5 text-xs", selectedModel === item.id ? "bg-white/15" : "bg-white text-slate-600")}>
                        {item.cost}
                      </span>
                    </div>
                    <div className={cn("mt-1 text-xs", selectedModel === item.id ? "text-slate-300" : "text-slate-500")}>{item.role}</div>
                  </button>
                ))}
              </div>
              <div className="mt-4 rounded-2xl border border-slate-100 bg-slate-50 p-3">
                <div className="text-xs font-bold uppercase tracking-wide text-slate-500">Selected endpoint</div>
                <code className="mt-1 block break-all text-xs text-slate-800">{model.endpoint}</code>
              </div>
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-4 md:grid-cols-4">
          <Metric icon={<Globe2 className="h-5 w-5" />} label="자동 수집 보드" value="크롤링 + AI" caption="유저 게시판 제외" />
          <Metric icon={<UserRound className="h-5 w-5" />} label="유저 게시판" value="수동 입력" caption="자동 수집 없음" />
          <Metric icon={<Layers3 className="h-5 w-5" />} label="실전 운용" value="Rule+Skill" caption="AGENTS.md 포함" />
          <Metric icon={<ShieldAlert className="h-5 w-5" />} label="MCP" value="권한 분리" caption="위험도 라벨링" />
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="relative min-w-0 flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Claude Code, AGENTS.md, Unity GC, MCP 검색"
                className="h-11 w-full rounded-2xl border border-slate-200 bg-slate-50 pl-10 pr-4 text-sm outline-none focus:border-blue-300 focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill active={selectedCategory === "전체"} onClick={() => setSelectedCategory("전체")}>전체</Pill>
              {categories.map((category) => (
                <Pill key={category} active={selectedCategory === category} onClick={() => setSelectedCategory(category)}>{category}</Pill>
              ))}
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 border-t border-slate-100 pt-3">
            <Pill active={selectedDomain === "전체"} onClick={() => setSelectedDomain("전체")}>전체 분야</Pill>
            {domains.map((domain) => (
              <Pill key={domain} active={selectedDomain === domain} onClick={() => setSelectedDomain(domain)}>
                <span className="inline-flex items-center gap-1">{domainIcon(domain)} {domain}</span>
              </Pill>
            ))}
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-[1fr_380px]">
          <div className="space-y-4">
            {filteredPosts.map((post) => (
              <Card key={post.id} className="rounded-3xl border-slate-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
                <CardContent className="p-5">
                  <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
                    <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-slate-700">
                      {domainIcon(post.domain)} {post.domain}
                    </span>
                    <span className="rounded-full bg-blue-50 px-2.5 py-1 text-blue-700">{post.category}</span>
                    <span className="rounded-full bg-purple-50 px-2.5 py-1 text-purple-700">{sourceLabel(post.sourceKind)}</span>
                    <span className={cn("rounded-full border px-2.5 py-1", riskClass(post.risk))}>risk {post.risk}</span>
                    <span className="ml-auto rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 font-bold text-emerald-700">{post.score}</span>
                  </div>

                  <h3 className="text-lg font-bold leading-snug">{post.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{post.summary}</p>

                  <div className="mt-3 flex flex-wrap gap-1.5 text-xs">
                    {post.sources.map((source) => (
                      <span key={source} className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">{source}</span>
                    ))}
                  </div>

                  <div className="mt-4 grid gap-3 md:grid-cols-3">
                    {post.rule && <MiniBlock title="Rule" value={post.rule} />}
                    {post.skill && <MiniBlock title="Skill" value={post.skill} />}
                    {post.agentRule && <MiniBlock title="AGENTS.md" value={post.agentRule} />}
                  </div>

                  {(post.badExample || post.goodExample) && (
                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                      {post.badExample && <CompareBox type="bad" title="나쁜 사용" text={post.badExample} />}
                      {post.goodExample && <CompareBox type="good" title="좋은 사용" text={post.goodExample} />}
                    </div>
                  )}

                  <div className="mt-4 rounded-2xl border border-slate-100 bg-slate-50 p-3">
                    <div className="text-xs font-bold uppercase tracking-wide text-slate-500">바로 적용</div>
                    <div className="mt-1 text-sm font-medium text-slate-800">{post.action}</div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <aside className="space-y-4">
            <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
              <CardContent className="p-5">
                <h2 className="flex items-center gap-2 text-lg font-bold">
                  <BookOpen className="h-5 w-5 text-emerald-600" /> 유저 게시판
                </h2>
                <p className="mt-1 text-sm leading-6 text-slate-600">
                  이 영역만 수동 입력 전용이다. 자동 크롤링/AI 합성 없이 실제 사용자 경험을 남긴다.
                </p>
                <div className="mt-4 grid gap-2">
                  <input
                    value={draftTitle}
                    onChange={(event) => setDraftTitle(event.target.value)}
                    placeholder="제목"
                    className="h-10 rounded-2xl border border-slate-200 bg-slate-50 px-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <textarea
                    value={draftBody}
                    onChange={(event) => setDraftBody(event.target.value)}
                    placeholder="실전 운영 팁 작성"
                    className="min-h-24 rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <Button className="rounded-2xl" onClick={() => { setDraftTitle(""); setDraftBody(""); }}>등록 Mock</Button>
                </div>
                <div className="mt-4 space-y-3">
                  {userPosts.map((post) => (
                    <div key={post.id} className="rounded-2xl border border-slate-100 bg-slate-50 p-3">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="font-semibold">{post.title}</div>
                          <div className="mt-1 text-xs text-slate-500">{post.author} · {post.createdAt}</div>
                        </div>
                        <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs text-emerald-700">수동 입력</span>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-slate-600">{post.body}</p>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {post.tags.map((tag) => <span key={tag} className="rounded-full bg-white px-2 py-0.5 text-xs text-slate-600">#{tag}</span>)}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
              <CardContent className="p-5">
                <h2 className="flex items-center gap-2 text-lg font-bold">
                  <Settings2 className="h-5 w-5" /> 실전 운용 템플릿
                </h2>
                <p className="mt-1 text-sm leading-6 text-slate-600">Rule + Skill + AGENTS.md를 한 카테고리로 합친 운영 템플릿.</p>
                <pre className="mt-4 max-h-[360px] overflow-auto rounded-2xl bg-slate-950 p-4 text-xs leading-5 text-slate-100">{agentsTemplate}</pre>
                <Button className="mt-4 w-full rounded-2xl" onClick={() => generateOpsTemplate(activeSetting)} disabled={generating}>
                  {generating ? "생성 중..." : "AI 템플릿 생성"}
                </Button>
                {template && (
                  <pre className="mt-4 max-h-[360px] overflow-auto rounded-2xl bg-slate-950 p-4 text-xs leading-5 text-slate-100">{template}</pre>
                )}
              </CardContent>
            </Card>

            <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
              <CardContent className="p-5 text-sm leading-6 text-slate-700">
                <h2 className="flex items-center gap-2 text-lg font-bold text-slate-950">
                  <AlertTriangle className="h-5 w-5 text-amber-500" /> Production 설계
                </h2>
                <ul className="mt-3 list-disc space-y-1 pl-5">
                  <li>FastAPI + PostgreSQL</li>
                  <li>Celery/RQ 크롤러</li>
                  <li>유저 게시판은 수동 입력만 허용</li>
                  <li>그 외 보드는 웹 크롤링 + AI 요약 + 축적 + 합성 데이터</li>
                  <li>LLM Router: 무료/로컬/유료 모델 역할 분리</li>
                  <li>추천 셋팅은 분야별 하루 1회 생성</li>
                </ul>
              </CardContent>
            </Card>
          </aside>
        </section>
      </main>
    </div>
  );
}

function Pill({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "rounded-full px-3 py-1.5 text-sm transition",
        active ? "bg-slate-950 text-white shadow-sm" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
      )}
    >
      {children}
    </button>
  );
}

function Metric({ icon, label, value, caption }: { icon: React.ReactNode; label: string; value: string; caption: string }) {
  return (
    <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
      <CardContent className="p-5">
        <div className="rounded-2xl bg-slate-100 p-2 text-slate-700 w-fit">{icon}</div>
        <div className="mt-4 text-sm font-medium text-slate-500">{label}</div>
        <div className="mt-1 text-2xl font-bold">{value}</div>
        <div className="mt-1 text-xs text-slate-500">{caption}</div>
      </CardContent>
    </Card>
  );
}

function InfoBlock({ title, icon, items, dark }: { title: string; icon: React.ReactNode; items: string[]; dark?: boolean }) {
  return (
    <div className={cn("rounded-2xl p-4", dark ? "bg-white/10 ring-1 ring-white/15" : "bg-slate-50")}>
      <div className={cn("flex items-center gap-2 text-sm font-bold", dark ? "text-blue-100" : "text-slate-800")}>{icon} {title}</div>
      <ul className={cn("mt-2 space-y-1.5 text-sm", dark ? "text-slate-200" : "text-slate-600")}>
        {items.map((item) => (
          <li key={item} className="flex gap-2">
            <span className={cn("mt-2 h-1.5 w-1.5 shrink-0 rounded-full", dark ? "bg-blue-300" : "bg-blue-500")} />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function MiniBlock({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-slate-50 p-3">
      <div className="text-xs font-bold uppercase tracking-wide text-slate-500">{title}</div>
      <div className="mt-1 text-sm text-slate-800">{value}</div>
    </div>
  );
}

function CompareBox({ type, title, text }: { type: "bad" | "good"; title: string; text: string }) {
  return (
    <div className={cn("rounded-2xl border p-3", type === "bad" ? "border-red-100 bg-red-50" : "border-emerald-100 bg-emerald-50")}>
      <div className={cn("text-xs font-bold", type === "bad" ? "text-red-700" : "text-emerald-700")}>{title}</div>
      <div className="mt-1 text-sm text-slate-700">{text}</div>
    </div>
  );
}
