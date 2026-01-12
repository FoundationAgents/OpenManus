import os

from celery import Celery

broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
backend_url = os.getenv("CELERY_RESULT_BACKEND", os.getenv("DATABASE_URL", "redis://redis:6379/0"))

celery_app = Celery("openmanus", broker=broker_url, backend=backend_url)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    task_always_eager=False,
)


__all__ = ["celery_app"]
