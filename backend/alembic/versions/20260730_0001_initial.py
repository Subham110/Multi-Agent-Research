"""Initial tenant, research, report, event, source, and vector-memory schema.

Revision ID: 20260730_0001
Revises:
Create Date: 2026-07-30
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "20260730_0001"
down_revision = None
branch_labels = None
depends_on = None

USER_ROLE = postgresql.ENUM("admin", "researcher", "viewer", name="userrole", create_type=False)
JOB_STATUS = postgresql.ENUM(
    "queued", "running", "completed", "failed", "cancelled", name="jobstatus", create_type=False
)
RESEARCH_DEPTH = postgresql.ENUM("quick", "standard", "deep", name="researchdepth", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    USER_ROLE.create(bind, checkfirst=True)
    JOB_STATUS.create(bind, checkfirst=True)
    RESEARCH_DEPTH.create(bind, checkfirst=True)

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=512), nullable=False),
        sa.Column("full_name", sa.String(length=160), server_default="Researcher", nullable=False),
        sa.Column("role", USER_ROLE, server_default="researcher", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"], unique=False)

    op.create_table(
        "research_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic", sa.String(length=500), nullable=False),
        sa.Column("objective", sa.Text(), server_default="", nullable=False),
        sa.Column("depth", RESEARCH_DEPTH, server_default="standard", nullable=False),
        sa.Column("status", JOB_STATUS, server_default="queued", nullable=False),
        sa.Column("current_agent", sa.String(length=80), nullable=True),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_reflections", sa.Integer(), server_default="2", nullable=False),
        sa.Column("max_revisions", sa.Integer(), server_default="2", nullable=False),
        sa.Column("config", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_jobs_created_by", "research_jobs", ["created_by"], unique=False)
    op.create_index("ix_research_jobs_status", "research_jobs", ["status"], unique=False)
    op.create_index("ix_research_jobs_tenant_id", "research_jobs", ["tenant_id"], unique=False)
    op.create_index("ix_research_jobs_tenant_created", "research_jobs", ["tenant_id", "created_at"], unique=False)

    op.create_table(
        "research_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("agent", sa.String(length=80), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["research_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "sequence", name="uq_event_job_sequence"),
    )
    op.create_index("ix_research_events_job_id", "research_events", ["job_id"], unique=False)
    op.create_index("ix_research_events_tenant_id", "research_events", ["tenant_id"], unique=False)
    op.create_index("ix_events_job_sequence", "research_events", ["job_id", "sequence"], unique=False)

    op.create_table(
        "research_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=40), server_default="web", nullable=False),
        sa.Column("authors", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("published_at", sa.String(length=80), nullable=True),
        sa.Column("abstract", sa.Text(), server_default="", nullable=False),
        sa.Column("excerpt", sa.Text(), server_default="", nullable=False),
        sa.Column("credibility_score", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["research_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "url", name="uq_source_job_url"),
    )
    op.create_index("ix_research_sources_job_id", "research_sources", ["job_id"], unique=False)
    op.create_index("ix_research_sources_tenant_id", "research_sources", ["tenant_id"], unique=False)

    op.create_table(
        "research_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("quality_score", sa.Integer(), nullable=False),
        sa.Column("citation_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("metadata", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["research_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index("ix_research_reports_tenant_id", "research_reports", ["tenant_id"], unique=False)

    op.create_table(
        "memory_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", sa.String(length=50), server_default="report", nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=False),
        sa.Column("metadata", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["research_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memory_chunks_tenant_id", "memory_chunks", ["tenant_id"], unique=False)
    op.create_index("ix_memory_tenant_created", "memory_chunks", ["tenant_id", "created_at"], unique=False)
    op.create_index(
        "ix_memory_embedding_hnsw",
        "memory_chunks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_memory_embedding_hnsw", table_name="memory_chunks")
    op.drop_index("ix_memory_tenant_created", table_name="memory_chunks")
    op.drop_index("ix_memory_chunks_tenant_id", table_name="memory_chunks")
    op.drop_table("memory_chunks")
    op.drop_index("ix_research_reports_tenant_id", table_name="research_reports")
    op.drop_table("research_reports")
    op.drop_index("ix_research_sources_tenant_id", table_name="research_sources")
    op.drop_index("ix_research_sources_job_id", table_name="research_sources")
    op.drop_table("research_sources")
    op.drop_index("ix_events_job_sequence", table_name="research_events")
    op.drop_index("ix_research_events_tenant_id", table_name="research_events")
    op.drop_index("ix_research_events_job_id", table_name="research_events")
    op.drop_table("research_events")
    op.drop_index("ix_research_jobs_tenant_created", table_name="research_jobs")
    op.drop_index("ix_research_jobs_tenant_id", table_name="research_jobs")
    op.drop_index("ix_research_jobs_status", table_name="research_jobs")
    op.drop_index("ix_research_jobs_created_by", table_name="research_jobs")
    op.drop_table("research_jobs")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_table("tenants")

    bind = op.get_bind()
    RESEARCH_DEPTH.drop(bind, checkfirst=True)
    JOB_STATUS.drop(bind, checkfirst=True)
    USER_ROLE.drop(bind, checkfirst=True)
