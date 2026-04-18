import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery = Celery(
    "queuepilot",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks", "scheduler"],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)
