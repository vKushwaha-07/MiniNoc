import os
from celery import Celery
from .config import settings

# Use SQLite for local development if Redis is not available
# In production (Docker), these env vars will point to Redis
BROKER_URL = os.getenv("CELERY_BROKER_URL", "sqlalchemy+sqlite:///celery_broker.db")
BACKEND_URL = os.getenv("CELERY_RESULT_BACKEND", "db+sqlite:///celery_results.db")

celery_app = Celery(
    "mini_noc",
    broker=BROKER_URL,
    backend=BACKEND_URL,
    include=["app.services.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Windows Support: 'solo' pool is required for Windows execution usually, 
    # but we configure it via command line. 
    # Here we just ensure basic config.
)

if __name__ == "__main__":
    celery_app.start()
