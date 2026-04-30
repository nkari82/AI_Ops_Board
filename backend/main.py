from contextlib import asynccontextmanager
from importlib import import_module
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware


def _load_runtime_dependencies() -> tuple[Any, Any, dict[str, Any], Any, Any, Any]:
    try:
        config_module = import_module("backend.config")
        db_module = import_module("backend.db")
        llm_module = import_module("backend.services.llm_router")
        error_tracker_module = import_module("backend.services.error_tracker")
        router_modules = {
            "posts": import_module("backend.api.posts"),
            "models": import_module("backend.api.models"),
            "crawl": import_module("backend.api.crawl"),
            "analyze": import_module("backend.api.analyze"),
            "ws": import_module("backend.api.ws"),
            "knowledge_templates": import_module("backend.api.knowledge_templates"),
            "templates": import_module("backend.api.templates"),
            "recommendations": import_module("backend.api.recommendations"),
            "health": import_module("backend.api.health"),
            "admin": import_module("backend.api.admin"),
        }
    except ModuleNotFoundError:
        config_module = import_module("config")
        db_module = import_module("db")
        llm_module = import_module("services.llm_router")
        error_tracker_module = import_module("services.error_tracker")
        router_modules = {
            "posts": import_module("api.posts"),
            "models": import_module("api.models"),
            "crawl": import_module("api.crawl"),
            "analyze": import_module("api.analyze"),
            "ws": import_module("api.ws"),
            "knowledge_templates": import_module("api.knowledge_templates"),
            "templates": import_module("api.templates"),
            "recommendations": import_module("api.recommendations"),
            "health": import_module("api.health"),
            "admin": import_module("api.admin"),
        }

    return (
        config_module.settings,
        db_module.init_db,
        router_modules,
        llm_module.LLMRouter,
        llm_module.LLMRouterError,
        error_tracker_module.error_tracker,
    )


settings, init_db, router_modules, LLMRouter, LLMRouterError, error_tracker = _load_runtime_dependencies()
posts = router_modules["posts"]
models = router_modules["models"]
crawl = router_modules["crawl"]
analyze = router_modules["analyze"]
ws = router_modules["ws"]
knowledge_templates = router_modules["knowledge_templates"]
templates = router_modules["templates"]
recommendations = router_modules["recommendations"]
health_api = router_modules["health"]
admin_api = router_modules["admin"]


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title="AI Ops Board API",
    description="AI-powered operations knowledge board backend",
    version="1.0.0",
    lifespan=lifespan,
)

def _default_text_provider() -> str:
    if settings.GOOGLE_AI_STUDIO_KEY:
        return "gemini"
    if settings.POLLINATIONS_API_KEY:
        return "pollinations"
    if settings.GROQ_API_KEY:
        return "groq"
    if settings.OPENROUTER_API_KEY:
        return "openrouter"
    if settings.MISTRAL_API_KEY:
        return "mistral"
    if settings.DEEPSEEK_API_KEY:
        return "deepseek"
    if settings.CEREBRAS_API_KEY:
        return "cerebras"
    if settings.SAMBANOVA_API_KEY:
        return "sambanova"
    if settings.HUGGINGFACE_TOKEN:
        return "huggingface"
    return "gemini"


class TestRequest(BaseModel):
    # Accept both old/new field names from UI
    message: str | None = None
    prompt: str | None = None
    provider: str | None = None


@app.post("/api/test-llm")
async def test_llm(request: TestRequest):
    msg = (request.message or request.prompt or "").strip()
    if not msg:
        raise HTTPException(status_code=422, detail="'message' (or 'prompt') is required")

    provider = request.provider or _default_text_provider()

    try:
        router = LLMRouter()
        response = await router.generate(msg, provider=provider)
        return {"status": "success", "provider": provider, "response": response}
    except LLMRouterError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"LLM 호출 실패 ({exc.provider}): {exc.message}",
        ) from exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
)

app.include_router(posts.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(crawl.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(ws.router, prefix="/api")
app.include_router(knowledge_templates.router, prefix="/api")
app.include_router(templates.router, prefix="/api")
app.include_router(recommendations.router, prefix="/api")
app.include_router(health_api.router, prefix="/api")
app.include_router(admin_api.router, prefix="/api")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_tracker.log_error(
        "UNHANDLED_EXCEPTION",
        str(exc),
        details={"path": str(request.url.path), "method": request.method},
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
async def root():
    return {
        "message": "AI Ops Board API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    # keep legacy endpoint but route through real dependency checks
    return await health_api.health_basic()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
