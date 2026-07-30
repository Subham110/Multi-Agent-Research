import asyncio
import json
import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException, status
from sqlalchemy import select

from app.core.config import settings
from app.db.models import ResearchEvent, ResearchJob, User
from app.db.session import SessionLocal

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/research/{job_id}")
async def research_stream(websocket: WebSocket, job_id: uuid.UUID, ticket: str) -> None:
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    ticket_payload = await redis_client.getdel(f"ws-ticket:{ticket}")
    if not ticket_payload:
        await redis_client.aclose()
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired ticket")
    try:
        payload = json.loads(ticket_payload)
        user_id = uuid.UUID(payload["user_id"])
        tenant_id = uuid.UUID(payload["tenant_id"])
    except (ValueError, KeyError, json.JSONDecodeError):
        await redis_client.aclose()
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid ticket") from None

    with SessionLocal() as db:
        user = db.get(User, user_id)
        job = db.scalar(select(ResearchJob).where(ResearchJob.id == job_id, ResearchJob.tenant_id == tenant_id))
        if not user or not user.is_active or user.tenant_id != tenant_id or not job:
            await redis_client.aclose()
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Not authorized")

    await websocket.accept()
    pubsub = redis_client.pubsub()
    channel = f"research:{job_id}"
    await pubsub.subscribe(channel)
    seen: set[str] = set()
    heartbeat = 0
    try:
        with SessionLocal() as db:
            events = db.scalars(
                select(ResearchEvent)
                .where(ResearchEvent.job_id == job_id, ResearchEvent.tenant_id == tenant_id)
                .order_by(ResearchEvent.sequence)
            ).all()
            for event in events:
                data = {
                    "id": str(event.id),
                    "sequence": event.sequence,
                    "event_type": event.event_type,
                    "agent": event.agent,
                    "message": event.message,
                    "payload": event.payload,
                    "created_at": event.created_at.isoformat(),
                }
                seen.add(data["id"])
                await websocket.send_json(data)
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                data = json.loads(message["data"])
                if data.get("id") not in seen:
                    seen.add(data["id"])
                    await websocket.send_json(data)
            heartbeat += 1
            if heartbeat >= 15:
                await websocket.send_json({"event_type": "heartbeat"})
                heartbeat = 0
            await asyncio.sleep(0.1)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        await redis_client.aclose()
