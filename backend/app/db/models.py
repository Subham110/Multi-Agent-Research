import enum
import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.config import settings


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    admin = "admin"
    researcher = "researcher"
    viewer = "viewer"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ResearchDepth(str, enum.Enum):
    quick = "quick"
    standard = "standard"
    deep = "deep"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    users: Mapped[list["User"]] = relationship(back_populates="tenant")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    hashed_password: Mapped[str] = mapped_column(String(512))
    full_name: Mapped[str] = mapped_column(String(160), default="Researcher")
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.researcher)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    tenant: Mapped[Tenant] = relationship(back_populates="users")
    jobs: Mapped[list["ResearchJob"]] = relationship(back_populates="creator")


class ResearchJob(Base):
    __tablename__ = "research_jobs"
    __table_args__ = (
        Index("ix_research_jobs_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    topic: Mapped[str] = mapped_column(String(500))
    objective: Mapped[str] = mapped_column(Text, default="")
    depth: Mapped[ResearchDepth] = mapped_column(Enum(ResearchDepth), default=ResearchDepth.standard)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.queued, index=True)
    current_agent: Mapped[str | None] = mapped_column(String(80), nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    max_reflections: Mapped[int] = mapped_column(Integer, default=2)
    max_revisions: Mapped[int] = mapped_column(Integer, default=2)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creator: Mapped[User] = relationship(back_populates="jobs")
    events: Mapped[list["ResearchEvent"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    sources: Mapped[list["ResearchSource"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    report: Mapped["ResearchReport | None"] = relationship(back_populates="job", cascade="all, delete-orphan", uselist=False)


class ResearchEvent(Base):
    __tablename__ = "research_events"
    __table_args__ = (
        Index("ix_events_job_sequence", "job_id", "sequence"),
        UniqueConstraint("job_id", "sequence", name="uq_event_job_sequence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("research_jobs.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(80))
    agent: Mapped[str | None] = mapped_column(String(80), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped[ResearchJob] = relationship(back_populates="events")


class ResearchSource(Base):
    __tablename__ = "research_sources"
    __table_args__ = (UniqueConstraint("job_id", "url", name="uq_source_job_url"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("research_jobs.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(40), default="web")
    authors: Mapped[list] = mapped_column(JSON, default=list)
    published_at: Mapped[str | None] = mapped_column(String(80), nullable=True)
    abstract: Mapped[str] = mapped_column(Text, default="")
    excerpt: Mapped[str] = mapped_column(Text, default="")
    credibility_score: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped[ResearchJob] = relationship(back_populates="sources")


class ResearchReport(Base):
    __tablename__ = "research_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("research_jobs.id", ondelete="CASCADE"), unique=True)
    title: Mapped[str] = mapped_column(Text)
    executive_summary: Mapped[str] = mapped_column(Text)
    markdown: Mapped[str] = mapped_column(Text)
    quality_score: Mapped[int] = mapped_column(Integer)
    citation_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    job: Mapped[ResearchJob] = relationship(back_populates="report")


class MemoryChunk(Base):
    __tablename__ = "memory_chunks"
    __table_args__ = (
        Index("ix_memory_tenant_created", "tenant_id", "created_at"),
        Index(
            "ix_memory_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("research_jobs.id", ondelete="SET NULL"), nullable=True)
    kind: Mapped[str] = mapped_column(String(50), default="report")
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.EMBEDDING_DIMENSION))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
