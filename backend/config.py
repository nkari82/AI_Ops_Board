from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost/ai_ops_board"
    
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: str = "AI Ops Board Crawler 1.0"
    REDDIT_USE_RSS: bool = True
    REDDIT_RSS_FEEDS: str = "https://www.reddit.com/r/LocalLLaMA/.rss,https://www.reddit.com/r/MachineLearning/.rss,https://www.reddit.com/r/LLMOps/.rss,https://www.reddit.com/r/ArtificialIntelligence/.rss"
    # RSS parsing/detail controls
    REDDIT_RSS_MAX_CONTENT_CHUNKS: int = 4
    REDDIT_RSS_MAX_LINKS_PER_ENTRY: int = 2
    REDDIT_RSS_FETCH_LINK_CONTENT: bool = True
    REDDIT_RSS_LINK_TIMEOUT_SECONDS: int = 6
    REDDIT_RSS_MAX_LINK_CONTENT_CHARS: int = 1200
    REDDIT_RSS_SELFTEXT_MAX_CHARS: int = 4000
    # Linked source quality gate controls
    REDDIT_RSS_LINK_MIN_TEXT_CHARS: int = 160
    REDDIT_RSS_LINK_MAX_NOISE_RATIO: float = 0.45
    REDDIT_RSS_LINK_MAX_SAME_LINE_RATIO: float = 0.6
    
    GITHUB_TOKEN: Optional[str] = None
    
    HUGGINGFACE_TOKEN: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    GOOGLE_AI_STUDIO_KEY: Optional[str] = None
    # Gemini model name (Generative Language API).
    # Recommended free-tier default: gemini-flash-latest
    GEMINI_MODEL: str = "gemini-flash-latest"
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com"
    OPENROUTER_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # Pollinations (OpenAI-compatible)
    POLLINATIONS_API_KEY: Optional[str] = None
    # Cheap default for general text tasks (templates/knowledge): "mistral" or "nova-fast"
    POLLINATIONS_TEXT_MODEL: str = "mistral"
    POLLINATIONS_BASE_URL: str = "https://gen.pollinations.ai"

    # Provider failover policy (quota-aware)
    LLM_FAILOVER_ENABLED: bool = True
    # Comma-separated provider preference chain
    LLM_FAILOVER_ORDER: str = "gemini,pollinations,groq,openrouter,huggingface,vllm"
    # HTTP statuses that should trigger failover attempts
    LLM_FAILOVER_ON_STATUS: str = "429,503,504"

    # Crawl control (env-driven)
    # Comma-separated source keys. e.g. "reddit,github,hn,youtube"
    CRAWL_ENABLED_SOURCES: str = "reddit,github,hn,youtube"
    # Default YouTube URLs for harness/ops crawling
    YOUTUBE_TARGET_URLS: str = ""
    # If true and target list is empty, /crawl/youtube accepts any URL.
    # Set false for strict allow-list policy.
    YOUTUBE_ALLOW_ALL_WHEN_TARGETS_EMPTY: bool = False
    # YouTube keyword-search crawl controls
    YOUTUBE_SEARCH_ENABLED: bool = True
    YOUTUBE_SEARCH_MAX_RESULTS: int = 8
    YOUTUBE_SEARCH_MAX_PAGES: int = 2
    # Dedup active task retention (seconds)
    YOUTUBE_SEARCH_DEDUP_TTL_SECONDS: int = 900
    # Request-level rate limit per query+window
    YOUTUBE_SEARCH_RATE_LIMIT_WINDOW_SECONDS: int = 60
    YOUTUBE_SEARCH_RATE_LIMIT_MAX_REQUESTS: int = 5
    # Minimum lengths for reliable classification/ingest
    # keep as str to tolerate empty env values from docker compose interpolation
    MIN_CLASSIFIABLE_CONTENT_LEN: str = "120"
    MIN_CLASSIFIABLE_SIGNAL_LEN: str = "160"
    
    VLLM_ENDPOINT: str = "http://localhost:8000/v1"
    
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3005", "http://localhost:5173", "http://frontend:3000"]
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
