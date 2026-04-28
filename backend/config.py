from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost/ai_ops_board"
    
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: str = "AI Ops Board Crawler 1.0"
    REDDIT_USE_RSS: bool = True
    REDDIT_RSS_FEEDS: str = "https://www.reddit.com/r/LocalLLaMA/.rss,https://www.reddit.com/r/ArtificialIntelligence/.rss"
    
    GITHUB_TOKEN: Optional[str] = None
    
    HUGGINGFACE_TOKEN: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    GOOGLE_AI_STUDIO_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    
    VLLM_ENDPOINT: str = "http://localhost:8000/v1"
    
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:3005", "http://localhost:5173", "http://frontend:3000"]
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
