from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..db.session import get_db
from ..core.celery_app import celery_app
import redis
import os

router = APIRouter(tags=["Health"])

@router.get("/health")
def health_check(response: Response, db: Session = Depends(get_db)):
    """
    Watchdog Health Check.
    Probes critical system components (DB, Redis) to ensure service is healthy.
    Returns 200 OK or 503 Service Unavailable.
    """
    status_report = {
        "status": "ok",
        "database": "unknown",
        "redis": "unknown"
    }
    
    # 1. Check Database
    try:
        db.execute(text("SELECT 1"))
        status_report["database"] = "ok"
    except Exception as e:
        status_report["database"] = f"error: {str(e)}"
        status_report["status"] = "degraded"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    # 2. Check Redis (if configured)
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            # We can use the celery broker connection or a direct redis client
            # Simple direct check:
            r = redis.from_url(redis_url)
            r.ping()
            status_report["redis"] = "ok"
        except Exception as e:
            status_report["redis"] = f"error: {str(e)}"
            # Redis might be critical for async tasks, so mark degraded
            status_report["status"] = "degraded" 
            # Note: We might decide Redis failure is not critical for READ ops, 
            # but for an MNC NOC it usually is. keeping 503 for now.
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        status_report["redis"] = "disabled"

    return status_report
