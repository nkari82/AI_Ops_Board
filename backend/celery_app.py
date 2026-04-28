from celery import Celery
from celery.schedules import crontab
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["api.crawl"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "crawl-reddit-daily": {
            "task": "api.crawl.background_crawl_reddit_task",
            "schedule": crontab(minute=0, hour=0),
            "args": ("LocalLLaMA", 20),
        },
    },
)
