from datetime import datetime

import redis
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.celery_app import celery
from app.config import get_settings
from app.database import get_db

settings = get_settings()
router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    return {"status": "healthy", "service": "meta-ads-audit-api", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/db")
def health_check_db(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "database": "query_failed"},
        )


@router.get("/health/ready")
def health_ready(db: Session = Depends(get_db)):
    checks = {"database": False, "redis": False, "worker": False}
    worker_snapshot = {"online_workers": 0}

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False

    try:
        client = redis.Redis.from_url(settings.redis_url)
        checks["redis"] = bool(client.ping())
    except Exception:
        checks["redis"] = False

    try:
        inspect = celery.control.inspect(timeout=0.5)
        pings = inspect.ping() if inspect else None
        online = len(pings or {})
        worker_snapshot["online_workers"] = online
        checks["worker"] = online > 0
    except Exception:
        checks["worker"] = False

    overall = all(checks.values())
    payload = {"status": "ready" if overall else "not_ready", "checks": checks, "worker_snapshot": worker_snapshot}
    if overall:
        return payload
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)
