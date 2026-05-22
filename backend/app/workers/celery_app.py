from celery import Celery

from app.core.config import settings
from app.core.sentry import configure_sentry


configure_sentry(service_name="worker")

celery_app = Celery(
    "advisor_signal_extraction",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)
