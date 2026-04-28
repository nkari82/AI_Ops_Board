import type { BoardCategory, Domain, LlmModel, OperationPost, RecommendedSetting } from "@/types";

export const domains: Domain[] = [
  "게임 클라이언트",
  "게임 서버",
  "프론트엔드",
  "백엔드",
  "Unity",
  "Unreal",
  "로컬 LLM",
  "Agent/MCP",
];

export const categories: BoardCategory[] = [
  "실전 운용",
  "아키텍처",
  "실전 사례",
  "깨알팁",
  "주의/함정",
  "플러그인/MCP",
];

export const operationPosts: OperationPost[] = [
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

export const models: LlmModel[] = [
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

export const recommendedSettings: RecommendedSetting[] = [
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

export const agentsTemplate = `# AGENTS.md

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
