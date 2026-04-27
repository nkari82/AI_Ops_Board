from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from db import init_db
from api import posts, models, crawl, analyze, ws, templates

app = FastAPI(
    title="AI Ops Board API",
    description="AI-powered operations knowledge board backend",
    version="1.0.0"
)

@app.on_event("startup")
async def startup():
    await init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(posts.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(crawl.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(ws.router, prefix="/api")
app.include_router(templates.router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "AI Ops Board API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
