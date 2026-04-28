export type Domain =
  | "게임 클라이언트"
  | "게임 서버"
  | "프론트엔드"
  | "백엔드"
  | "Unity"
  | "Unreal"
  | "로컬 LLM"
  | "Agent/MCP";

export type BoardCategory =
  | "실전 운용"
  | "아키텍처"
  | "실전 사례"
  | "깨알팁"
  | "주의/함정"
  | "플러그인/MCP";

export type SourceKind =
  | "crawled"
  | "ai_summarized"
  | "accumulated"
  | "ai_synthesized"
  | "manual_user_input";

export type OperationPost = {
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

export type UserPost = {
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

export type LlmModel = {
  id: string;
  name: string;
  provider: "Local" | "Groq" | "Google AI Studio" | "OpenRouter" | "Claude" | "OpenAI";
  cost: "free" | "cheap" | "paid";
  role: string;
  endpoint: string;
  enabled: boolean;
};

export type RecommendedSetting = {
  domain: Domain;
  title: string;
  score: number;
  modelRouting: string[];
  workflow: string[];
  mcp: string[];
  rules: string[];
  reason: string;
};
