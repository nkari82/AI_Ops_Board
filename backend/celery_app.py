from celery import Celery
from celery.schedules import crontab
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def _enabled_sources() -> set[str]:
    raw = (os.getenv("CRAWL_ENABLED_SOURCES", "reddit,github,hn,youtube") or "").strip()
    if not raw:
        return {"reddit", "github", "hn", "youtube"}
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


celery_app = Celery(
    "worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["api.crawl"]
)

beat_schedule = {}
enabled = _enabled_sources()
if "reddit" in enabled:
    beat_schedule["crawl-reddit-daily"] = {
        "task": "api.crawl.background_crawl_reddit_task",
        "schedule": crontab(minute=0, hour=0),
        "args": ("LocalLLaMA", 20),
    }

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule=beat_schedule,
)
