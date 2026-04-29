from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost/ai_ops_board"
    
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: str = "AI Ops Board Crawler 1.0"
    REDDIT_USE_RSS: bool = True
    REDDIT_RSS_FEEDS: str = "https://www.reddit.com/r/LocalLLaMA/.rss,https://www.reddit.com/r/MachineLearning/.rss,https://www.reddit.com/r/LLMOps/.rss,https://www.reddit.com/r/ArtificialIntelligence/.rss"
    
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

    # Crawl control (env-driven)
    # Comma-separated source keys. e.g. "reddit,github,hn,youtube"
    CRAWL_ENABLED_SOURCES: str = "reddit,github,hn,youtube"
    # Default YouTube URLs for harness/ops crawling
    YOUTUBE_TARGET_URLS: str = ""
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
