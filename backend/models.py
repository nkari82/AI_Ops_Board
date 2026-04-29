from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class Domain(str, Enum):
    게임_클라이언트 = "게임 클라이언트"
    게임_서버 = "게임 서버"
    프론트엔드 = "프론트엔드"
    백엔드 = "백엔드"
    Unity = "Unity"
    Unreal = "Unreal"
    로컬_LLM = "로컬 LLM"
    Agent_MCP = "Agent/MCP"
    기타 = "기타"


class BoardCategory(str, Enum):
    실전_운용 = "실전 운용"
    아키텍처 = "아키텍처"
    실전_사례 = "실전 사례"
    깨알팁 = "깨알팁"
    주의_함정 = "주의/함정"
    플러그인_MCP = "플러그인/MCP"


class SourceKind(str, Enum):
    crawled = "crawled"
    ai_summarized = "ai_summarized"
    accumulated = "accumulated"
    ai_synthesized = "ai_synthesized"
    manual_user_input = "manual_user_input"


class OperationPost(BaseModel):
    id: int
    title: str
    title_ko: str | None = None
    summary: str
    summary_ko: str | None = None
    content: str
    category: BoardCategory
    doc_type: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    domain: Domain
    score: int
    source_kind: SourceKind
    sources: list[str]
    updated_at: datetime
    rule: str | None = None
    skill: str | None = None
    agent_rule: str | None = None
    bad_example: str | None = None
    good_example: str | None = None
    action: str | None = None
    tags: list[str] = Field(default_factory=list)
    risk: str | None = None  # low, medium, high


class LlmModel(BaseModel):
    id: str
    name: str
    provider: str  # Local, Groq, Google AI Studio, OpenRouter, Claude, OpenAI
    cost: str  # free, cheap, paid
    role: str
    endpoint: str
    enabled: bool


class CrawlRequest(BaseModel):
    subreddit: str | None = None
    limit: int = 10


class AnalyzeRequest(BaseModel):
    content: str
    source_url: str
    domain: Domain | None = None
