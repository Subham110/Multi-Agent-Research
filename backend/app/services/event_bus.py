import contextlib
import json
import uuid
from datetime import UTC

import redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ResearchEvent


class EventPublisher:
    def __init__(self, db: Session, job_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        self.db = db
        self.job_id = job_id
        self.tenant_id = tenant_id
        self.redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

    def publish(
        self,
        event_type: str,
        message: str,
        *,
        agent: str | None = None,
        payload: dict | None = None,
    ) -> dict:
        key = f"research:{self.job_id}:sequence"
        try:
            sequence = int(self.redis.incr(key))
        except redis.RedisError:
            # PostgreSQL is the durable source of truth. This fallback keeps a run
            # progressing during a transient Redis transport interruption.
            sequence = (
                self.db.scalar(
                    select(func.max(ResearchEvent.sequence)).where(
                        ResearchEvent.job_id == self.job_id
                    )
                )
                or 0
            ) + 1
        event = ResearchEvent(
            tenant_id=self.tenant_id,
            job_id=self.job_id,
            sequence=sequence,
            event_type=event_type,
            agent=agent,
            message=message,
            payload=payload or {},
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        serialized = {
            "id": str(event.id),
            "sequence": event.sequence,
            "event_type": event.event_type,
            "agent": event.agent,
            "message": event.message,
            "payload": event.payload,
            "created_at": event.created_at.astimezone(UTC).isoformat(),
        }
        with contextlib.suppress(redis.RedisError):
            self.redis.publish(f"research:{self.job_id}", json.dumps(serialized))
        return serialized

    @staticmethod
    def ensure_sequence(db: Session, job_id: uuid.UUID) -> int:
        value = db.scalar(select(func.max(ResearchEvent.sequence)).where(ResearchEvent.job_id == job_id)) or 0
        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        key = f"research:{job_id}:sequence"
        try:
            with contextlib.suppress(redis.RedisError):
                current = client.get(key)
                if current is None or int(current) < value:
                    client.set(key, value)
        finally:
            client.close()
        return value
