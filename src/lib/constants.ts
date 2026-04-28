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

export const operationPosts: OperationPost[] = [];


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

export const recommendedSettings: RecommendedSetting[] = [];

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
