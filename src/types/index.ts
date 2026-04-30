export type Domain =
  | "게임 클라이언트"
  | "게임 서버"
  | "프론트엔드"
  | "백엔드"
  | "Unity"
  | "Unreal"
  | "로컬 LLM"
  | "Agent/MCP"
  | "기타";

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
  titleKo?: string | null;
  summary: string;
  summaryKo?: string | null;
  content: string;
  category: BoardCategory;
  docType: string | null;
  techStack: string[];
  domain: Domain;
  score: number;
  sourceKind: Exclude<SourceKind, "manual_user_input">;
  sources: string[];
  updatedAt: string;
  rule?: string;
  skill?: string;
  agentRule?: string;
  badExample?: string;
  goodExample?: string;
  action: string | null;
  tags: string[];
  risk: "low" | "medium" | "high" | null;
};

export type OperationPostApi = {
  id: number;
  title: string;
  title_ko?: string | null;
  summary: string;
  summary_ko?: string | null;
  content: string;
  category: BoardCategory;
  doc_type: string | null;
  tech_stack: string[];
  domain: Domain;
  score: number;
  source_kind: Exclude<SourceKind, "manual_user_input">;
  sources: string[];
  updated_at: string;
  rule?: string | null;
  skill?: string | null;
  agent_rule?: string | null;
  bad_example?: string | null;
  good_example?: string | null;
  action: string | null;
  tags: string[];
  risk: "low" | "medium" | "high" | null;
};

export type KnowledgeCard = {
  title: string;
  content: string;
  category?: string;
  type?: string;
  tech_stack?: string[];
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
  provider: "Local" | "Groq" | "Google AI Studio" | "OpenRouter" | "Claude" | "OpenAI" | "Codex CLI";
  cost: "free" | "cheap" | "paid" | "subscription";
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
  evidenceCount?: number;
  feedbackCount?: number;
  qualityConfidence?: number;
  qualityBand?: "low" | "medium" | "high";
  scoreBreakdown?: {
    baseScore: number;
    feedbackBonus: number;
    comboBoost: number;
    sparsePenaltyApplied: boolean;
    finalScore: number;
  };
  evidenceHighlights?: string[];
  subagentCandidates?: string[];
  dynamicViews?: string[];
  officialCategories?: {
    opencode: string[];
    claudecode: string[];
  };
  recommendationSnapshot?: {
    computedAt: string;
    domain: string;
    inputFilters: {
      clientEngine: string;
      gameGenre: string;
      devLanguage: string;
    };
    evidenceCount: number;
    feedbackCount: number;
    topCategories: string[];
    topTech: string[];
    selectedModels: string[];
    selectedWorkflow: string[];
  };
  recommendationSnapshotId?: string;
};
