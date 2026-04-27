from pydantic import BaseModel
from typing import Optional, List
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
    category: BoardCategory
    domain: Domain
    score: int
    source_kind: SourceKind
    sources: List[str]
    updated_at: datetime
    summary: str
    rule: Optional[str] = None
    skill: Optional[str] = None
    agent_rule: Optional[str] = None
    bad_example: Optional[str] = None
    good_example: Optional[str] = None
    action: str
    tags: List[str]
    risk: str  # low, medium, high


class LlmModel(BaseModel):
    id: str
    name: str
    provider: str  # Local, Groq, Google AI Studio, OpenRouter, Claude, OpenAI
    cost: str  # free, cheap, paid
    role: str
    endpoint: str
    enabled: bool


class CrawlRequest(BaseModel):
    subreddit: Optional[str] = None
    limit: int = 10


class AnalyzeRequest(BaseModel):
    content: str
    source_url: str
    domain: Optional[Domain] = None
