const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8005";

export async function fetchKnowledgeApi(): Promise<unknown[]> {
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
  const response = await fetch(`${API_BASE}/api/templates/generate-zip?domain=${domain}`, {
    method: "POST",
  });
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
