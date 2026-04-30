import type { KnowledgeCard, OperationPost, OperationPostApi, RecommendedSetting } from "@/types";

const DEFAULT_TIMEOUT_MS = 15000;

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

function resolveApiBase(): string {
  const explicitBase = (process.env.NEXT_PUBLIC_API_URL || "").trim();
  if (explicitBase) {
    return trimTrailingSlash(explicitBase);
  }

  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    const isLocalHost = hostname === "localhost" || hostname === "127.0.0.1";
    if (isLocalHost) {
      return "http://localhost:8005";
    }
    return `${protocol}//${hostname}:8005`;
  }

  return "http://localhost:8005";
}

const API_BASE = resolveApiBase();

export class ApiError extends Error {
  status: number;
  payload?: unknown;

  constructor(message: string, status: number, payload?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

async function fetchWithTimeout(input: RequestInfo | URL, init?: RequestInit, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const signal = init?.signal;
  if (signal) {
    signal.addEventListener("abort", () => controller.abort(), { once: true });
  }

  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } catch (error) {
    if (isAbortError(error)) {
      throw new ApiError("요청이 취소되었거나 시간 초과되었습니다.", 408);
    }
    throw new ApiError(
      "백엔드에 연결하지 못했습니다. 서버 실행 상태와 NEXT_PUBLIC_API_URL 설정을 확인하세요.",
      0,
      error,
    );
  } finally {
    clearTimeout(timeoutId);
  }
}

async function parseErrorMessage(response: Response): Promise<{ message: string; payload?: unknown }> {
  const contentType = response.headers.get("content-type") || "";
  try {
    if (contentType.includes("application/json")) {
      const payload = await response.json();
      const detail =
        typeof payload === "object" && payload !== null && "detail" in payload
          ? (payload as { detail?: unknown }).detail
          : undefined;
      const message = typeof detail === "string" ? detail : `요청 실패 (${response.status})`;
      return { message, payload };
    }

    const text = await response.text();
    return { message: text || `요청 실패 (${response.status})` };
  } catch {
    return { message: `요청 실패 (${response.status})` };
  }
}

async function ensureOk(response: Response, fallbackMessage: string): Promise<Response> {
  if (response.ok) return response;
  const parsed = await parseErrorMessage(response);
  throw new ApiError(parsed.message || fallbackMessage, response.status, parsed.payload);
}

function mapOperationPost(post: OperationPostApi): OperationPost {
  return {
    id: post.id,
    title: post.title,
    titleKo: post.title_ko ?? null,
    summary: post.summary,
    summaryKo: post.summary_ko ?? null,
    content: typeof post.content === "string" ? post.content : "",
    category: post.category,
    docType: post.doc_type,
    techStack: Array.isArray(post.tech_stack) ? post.tech_stack : [],
    domain: post.domain,
    score: post.score,
    sourceKind: post.source_kind,
    sources: Array.isArray(post.sources) ? post.sources : [],
    updatedAt: post.updated_at,
    rule: post.rule ?? undefined,
    skill: post.skill ?? undefined,
    agentRule: post.agent_rule ?? undefined,
    badExample: post.bad_example ?? undefined,
    goodExample: post.good_example ?? undefined,
    action: post.action,
    tags: Array.isArray(post.tags) ? post.tags : [],
    risk: post.risk,
  };
}

export async function fetchKnowledgeApi(signal?: AbortSignal): Promise<KnowledgeCard[]> {
  const response = await fetchWithTimeout(`${API_BASE}/api/knowledge`, { signal });
  await ensureOk(response, "지식 카드 조회 실패");
  return response.json();
}

export async function generateOpsTemplateApi(domain: string): Promise<{ template: string }> {
  const response = await fetchWithTimeout(`${API_BASE}/api/templates/generate?domain=${domain}`, {
    method: "POST",
  });
  await ensureOk(response, "템플릿 생성 실패");
  return response.json();
}

export async function downloadTemplateApi(
  domain: string,
  recommendation?: {
    harnessType?: string;
    modelRouting?: string[];
    workflow?: string[];
    mcp?: string[];
    rules?: string[];
    reason?: string;
    subagentCandidates?: string[];
    dynamicViews?: string[];
    officialCategories?: {
      opencode: string[];
      claudecode: string[];
    };
  },
): Promise<Blob> {
  const response = await fetchWithTimeout(`${API_BASE}/api/ops-templates/generate-zip?domain=${encodeURIComponent(domain)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(recommendation ?? {}),
  });
  await ensureOk(response, "템플릿 ZIP 생성 실패");
  return response.blob();
}

export async function crawlRedditApi(subreddit: string, limit: number): Promise<Response> {
  const response = await fetchWithTimeout(`${API_BASE}/api/crawl/reddit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ subreddit, limit }),
  });
  return ensureOk(response, "Reddit 크롤 요청 실패");
}

export async function crawlGithubApi(limit: number): Promise<Response> {
  const response = await fetchWithTimeout(`${API_BASE}/api/crawl/github?limit=${limit}`, { method: "POST" });
  return ensureOk(response, "GitHub 크롤 요청 실패");
}

export async function crawlHnApi(limit: number): Promise<Response> {
  const response = await fetchWithTimeout(`${API_BASE}/api/crawl/hn?limit=${limit}`, { method: "POST" });
  return ensureOk(response, "HN 크롤 요청 실패");
}

export async function crawlGeekNewsApi(limit: number): Promise<Response> {
  const response = await fetchWithTimeout(`${API_BASE}/api/crawl/geeknews?limit=${limit}`, { method: "POST" });
  return ensureOk(response, "GeekNews 크롤 요청 실패");
}

export async function crawlYoutubeApi(url: string): Promise<Response> {
  const response = await fetchWithTimeout(`${API_BASE}/api/crawl/youtube`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  return ensureOk(response, "YouTube URL 크롤 요청 실패");
}

export async function crawlYoutubeSearchApi(payload: {
  query: string;
  max_results?: number;
  pages?: number;
}): Promise<Response> {
  const response = await fetchWithTimeout(`${API_BASE}/api/crawl/youtube/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return ensureOk(response, "YouTube 검색 크롤 요청 실패");
}

export async function fetchCrawlTaskStatusApi(taskId: string): Promise<{
  task_id: string;
  status: string;
  result: unknown;
}> {
  const response = await fetchWithTimeout(`${API_BASE}/api/crawl/status/${encodeURIComponent(taskId)}`);
  await ensureOk(response, "크롤 상태 조회 실패");
  return response.json();
}

export async function fetchOperationPostsApi(signal?: AbortSignal): Promise<OperationPost[]> {
  const response = await fetchWithTimeout(`${API_BASE}/api/operation-posts`, { signal });
  await ensureOk(response, "운용 포스트 조회 실패");
  const data: OperationPostApi[] = await response.json();
  return data.map(mapOperationPost);
}

export async function fetchRecommendedSettingsApi(params?: {
  client_engine?: string;
  game_genre?: string;
  dev_language?: string;
}): Promise<RecommendedSetting[]> {
  const search = new URLSearchParams();
  if (params?.client_engine) search.set("client_engine", params.client_engine);
  if (params?.game_genre) search.set("game_genre", params.game_genre);
  if (params?.dev_language) search.set("dev_language", params.dev_language);
  const query = search.toString();
  const response = await fetchWithTimeout(`${API_BASE}/api/recommendations${query ? `?${query}` : ""}`);
  await ensureOk(response, "추천 설정 조회 실패");
  return response.json();
}

export async function sendRecommendationFeedbackApi(payload: {
  domain: string;
  rating: number;
  note?: string;
  chosen_models?: string[];
  chosen_workflow?: string[];
}): Promise<void> {
  const response = await fetchWithTimeout(`${API_BASE}/api/recommendations/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await ensureOk(response, "추천 피드백 저장 실패");
}

export async function getCloneInstructionsApi(domain: string): Promise<{ domain: string; script: string; hint: string }> {
  const response = await fetchWithTimeout(`${API_BASE}/api/ops-templates/clone-instructions?domain=${encodeURIComponent(domain)}`);
  await ensureOk(response, "클론 안내 생성 실패");
  return response.json();
}

export async function fetchAdminMetricsApi(): Promise<{
  quality: {
    totalPosts?: number;
    pollutedPosts?: number;
    qualityScore?: number;
  };
  errors: {
    total?: number;
    byCategory?: Record<string, number>;
  };
  youtubeSearch?: {
    requested?: number;
    deduplicated?: number;
    queued?: number;
    completed?: number;
    failed?: number;
    rateLimited?: number;
    activeCount?: number;
    lastQuery?: string | null;
    lastTaskId?: string | null;
    lastStatus?: string | null;
    updatedAt?: string | null;
    recentTaskSummaries?: Array<{
      taskId?: string;
      query?: string;
      status?: string;
      resultCount?: number | null;
      completedAt?: string;
    }>;
  };
  rssQuality?: {
    entryBlocksTotal?: number;
    extractedLinksTotal?: number;
    acceptedLinksTotal?: number;
    skippedLinksTotal?: number;
    acceptanceRate?: number | null;
    skippedByReason?: Record<string, number>;
  };
}> {
  const response = await fetchWithTimeout(`${API_BASE}/api/admin/metrics`);
  await ensureOk(response, "운영 지표 조회 실패");
  return response.json();
}

export async function fetchHealthDetailedApi(): Promise<{
  status: string;
  timestamp?: string;
  sloBreached?: boolean;
  checks?: Record<string, unknown>;
}> {
  const response = await fetchWithTimeout(`${API_BASE}/api/health/detailed`);
  await ensureOk(response, "헬스 상태 조회 실패");
  return response.json();
}

export async function fetchCrawlHealthApi(): Promise<{
  status: string;
  sources: Record<string, { status: string; detail?: string }>;
  timestamp: string;
}> {
  const response = await fetchWithTimeout(`${API_BASE}/api/crawl/health`);
  await ensureOk(response, "크롤링 헬스 조회 실패");
  return response.json();
}

export async function testLlmApi(prompt = "health check", provider?: string): Promise<{
  status: string;
  provider?: string;
  response?: string;
  detail?: string;
}> {
  const response = await fetchWithTimeout(
    `${API_BASE}/api/test-llm`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, provider }),
    },
    20000,
  );
  await ensureOk(response, "LLM 테스트 실패");
  return response.json();
}

