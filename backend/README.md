# AI Ops Board Backend

FastAPI backend for AI Ops Board - Crawler + LLM Pipeline

## Setup

```bash
cd backend
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

## API Endpoints

- `GET /api/operation-posts` - Get operation posts
- `GET /api/domains` - Get domains
- `GET /api/models` - Get LLM models
- `POST /api/crawl/reddit` - Trigger Reddit crawl
- `POST /api/crawl/github` - Trigger GitHub crawl
- `POST /api/crawl/hn` - Trigger HN crawl
- `POST /api/analyze` - Trigger AI analysis

## Architecture

```
backend/
├── api/           # FastAPI routes
├── crawlers/      # Web crawlers
├── services/      # Business logic
└── models/        # Pydantic models
```