import type { KnowledgeCard, OperationPost, OperationPostApi, RecommendedSetting } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8005";

function mapOperationPost(post: OperationPostApi): OperationPost {
  return {
    id: post.id,
    title: post.title,
    titleKo: post.title_ko ?? null,
    summary: post.summary,
    summaryKo: post.summary_ko ?? null,
    content: post.content,
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

export async function fetchKnowledgeApi(): Promise<KnowledgeCard[]> {
  const response = await fetch(`${API_BASE}/api/knowledge`);
  return response.json();
}

export async function generateOpsTemplateApi(domain: string): Promise<{ template: string }> {
  const response = await fetch(`${API_BASE}/api/templates/generate?domain=${domain}`, {
    method: "POST",
  });
  return response.json();
}

export async function downloadTemplateApi(domain: string): Promise<Blob> {
  const response = await fetch(`${API_BASE}/api/ops-templates/generate-zip?domain=${encodeURIComponent(domain)}`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("템플릿 ZIP 생성 실패");
  return response.blob();
}

export async function crawlRedditApi(subreddit: string, limit: number): Promise<Response> {
  return fetch(`${API_BASE}/api/crawl/reddit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ subreddit, limit }),
  });
}

export async function crawlGithubApi(limit: number): Promise<Response> {
  return fetch(`${API_BASE}/api/crawl/github?limit=${limit}`, { method: "POST" });
}

export async function crawlHnApi(limit: number): Promise<Response> {
  return fetch(`${API_BASE}/api/crawl/hn?limit=${limit}`, { method: "POST" });
}

export async function fetchOperationPostsApi(): Promise<OperationPost[]> {
  const response = await fetch(`${API_BASE}/api/operation-posts`);
  const data: OperationPostApi[] = await response.json();
  return data.map(mapOperationPost);
}

export async function fetchRecommendedSettingsApi(): Promise<RecommendedSetting[]> {
  const response = await fetch(`${API_BASE}/api/recommendations`);
  if (!response.ok) throw new Error("추천 설정 조회 실패");
  return response.json();
}

export async function sendRecommendationFeedbackApi(payload: {
  domain: string;
  rating: number;
  note?: string;
  chosen_models?: string[];
  chosen_workflow?: string[];
}): Promise<void> {
  const response = await fetch(`${API_BASE}/api/recommendations/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("추천 피드백 저장 실패");
}

export async function getCloneInstructionsApi(domain: string): Promise<{ domain: string; script: string; hint: string }> {
  const response = await fetch(`${API_BASE}/api/ops-templates/clone-instructions?domain=${encodeURIComponent(domain)}`);
  if (!response.ok) throw new Error("클론 안내 생성 실패");
  return response.json();
}

