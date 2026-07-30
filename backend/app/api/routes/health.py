import redis
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "healthy", "service": settings.APP_NAME}


@router.get("/ready")
def ready() -> dict:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        client = redis.Redis.from_url(settings.REDIS_URL)
        try:
            client.ping()
        finally:
            client.close()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Dependencies unavailable") from exc
    return {"status": "ready"}
