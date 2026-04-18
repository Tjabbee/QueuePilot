"""
Celery app configuration for QueuePilot.

Initializes the shared Celery instance used by tasks and the beat scheduler.
Uses Redis for both broker and result backend. Settings are tuned for I/O-heavy
HTTP operations (logins, queue point checks).
"""
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
    worker_prefetch_multiplier=1,  # one task at a time — HTTP logins are I/O-heavy
    task_acks_late=True,           # re-queue on worker crash; prevents lost tasks
)
