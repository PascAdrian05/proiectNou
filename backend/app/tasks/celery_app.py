from celery import Celery
from celery.schedules import crontab

from app.core.config import settings


celery_app = Celery(
    "security_monitor",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)

celery_app.conf.beat_schedule = {
    "check-scheduled-scans": {
        "task": "scan.check_scheduled",
        "schedule": 60.0,
    },
}


import app.tasks.scan_tasks  # noqa: E402,F401
import app.tasks.scheduled_tasks  # noqa: E402,F401
