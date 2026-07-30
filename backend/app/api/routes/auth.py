import json
import secrets

import redis
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import Tenant, User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse, WSTicketResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def serialize_user(user: User, tenant: Tenant) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        tenant_id=str(user.tenant_id),
        tenant_slug=tenant.slug,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    tenant = db.scalar(select(Tenant).where(Tenant.slug == payload.tenant_slug, Tenant.is_active.is_(True)))
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    user = db.scalar(
        select(User).where(
            User.tenant_id == tenant.id,
            User.email == payload.email.lower(),
            User.is_active.is_(True),
        )
    )
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role.value)
    return TokenResponse(access_token=token, user=serialize_user(user, tenant))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession) -> TokenResponse:
    if not settings.ALLOW_REGISTRATION:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Registration is disabled")
    tenant = db.scalar(select(Tenant).where(Tenant.slug == payload.tenant_slug, Tenant.is_active.is_(True)))
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    exists = db.scalar(select(User.id).where(User.tenant_id == tenant.id, User.email == payload.email.lower()))
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        tenant_id=tenant.id,
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=UserRole.researcher,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role.value)
    return TokenResponse(access_token=token, user=serialize_user(user, tenant))


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser, db: DbSession) -> UserResponse:
    tenant = db.get(Tenant, current_user.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return serialize_user(current_user, tenant)


@router.post("/ws-ticket", response_model=WSTicketResponse)
def create_ws_ticket(current_user: CurrentUser) -> WSTicketResponse:
    ticket = secrets.token_urlsafe(32)
    client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        client.setex(
            f"ws-ticket:{ticket}",
            60,
            json.dumps({"user_id": str(current_user.id), "tenant_id": str(current_user.tenant_id)}),
        )
    finally:
        client.close()
    return WSTicketResponse(ticket=ticket)
