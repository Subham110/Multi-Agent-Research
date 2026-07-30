import uuid
from datetime import UTC

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.db.models import (
    JobStatus,
    ResearchDepth,
    ResearchEvent,
    ResearchJob,
    ResearchReport,
    ResearchSource,
    UserRole,
)
from app.schemas.research import (
    DashboardStats,
    ReportResponse,
    ResearchCreate,
    ResearchEventResponse,
    ResearchJobResponse,
    SourceResponse,
)
from app.services.event_bus import EventPublisher
from app.tasks.research import run_research_job
from app.worker import celery_app

router = APIRouter(prefix="/research", tags=["research"])


def serialize_source(source: ResearchSource) -> SourceResponse:
    return SourceResponse(
        id=str(source.id),
        title=source.title,
        url=source.url,
        source_type=source.source_type,
        authors=source.authors,
        published_at=source.published_at,
        abstract=source.abstract,
        excerpt=source.excerpt,
        credibility_score=source.credibility_score,
    )


def serialize_report(report: ResearchReport | None) -> ReportResponse | None:
    if report is None:
        return None
    return ReportResponse(
        id=str(report.id),
        title=report.title,
        executive_summary=report.executive_summary,
        markdown=report.markdown,
        quality_score=report.quality_score,
        citation_count=report.citation_count,
        metadata=report.metadata_json,
        version=report.version,
        created_at=report.created_at,
    )


def serialize_job(job: ResearchJob) -> ResearchJobResponse:
    return ResearchJobResponse(
        id=str(job.id),
        topic=job.topic,
        objective=job.objective,
        depth=job.depth.value,
        status=job.status.value,
        current_agent=job.current_agent,
        progress=job.progress,
        error=job.error,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        report=serialize_report(job.report),
        sources=[serialize_source(source) for source in job.sources],
    )


def get_tenant_job(db: DbSession, current_user: CurrentUser, job_id: uuid.UUID) -> ResearchJob:
    job = db.scalar(
        select(ResearchJob)
        .options(selectinload(ResearchJob.report), selectinload(ResearchJob.sources))
        .where(ResearchJob.id == job_id, ResearchJob.tenant_id == current_user.tenant_id)
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research job not found")
    return job


@router.post("", response_model=ResearchJobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_research(payload: ResearchCreate, current_user: CurrentUser, db: DbSession) -> ResearchJobResponse:
    if current_user.role == UserRole.viewer:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewer role cannot launch research")
    active_jobs = db.scalar(
        select(func.count()).select_from(ResearchJob).where(
            ResearchJob.created_by == current_user.id,
            ResearchJob.status.in_([JobStatus.queued, JobStatus.running]),
        )
    ) or 0
    if active_jobs >= settings.MAX_ACTIVE_JOBS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum active research jobs reached ({settings.MAX_ACTIVE_JOBS_PER_USER})",
        )
    job = ResearchJob(
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        topic=payload.topic.strip(),
        objective=payload.objective.strip(),
        depth=ResearchDepth(payload.depth),
        max_reflections=payload.max_reflections,
        max_revisions=payload.max_revisions,
        config={"focus_urls": [str(url) for url in payload.focus_urls]},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    task = run_research_job.delay(str(job.id))
    job.config = {**job.config, "celery_task_id": task.id}
    db.commit()
    return serialize_job(job)


@router.get("", response_model=list[ResearchJobResponse])
def list_research(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ResearchJobResponse]:
    jobs = db.scalars(
        select(ResearchJob)
        .options(selectinload(ResearchJob.report), selectinload(ResearchJob.sources))
        .where(ResearchJob.tenant_id == current_user.tenant_id)
        .order_by(ResearchJob.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [serialize_job(job) for job in jobs]


@router.get("/stats", response_model=DashboardStats)
def stats(current_user: CurrentUser, db: DbSession) -> DashboardStats:
    tenant_filter = ResearchJob.tenant_id == current_user.tenant_id
    total_jobs = db.scalar(select(func.count()).select_from(ResearchJob).where(tenant_filter)) or 0
    completed_jobs = db.scalar(
        select(func.count()).select_from(ResearchJob).where(tenant_filter, ResearchJob.status == JobStatus.completed)
    ) or 0
    running_jobs = db.scalar(
        select(func.count()).select_from(ResearchJob).where(tenant_filter, ResearchJob.status.in_([JobStatus.queued, JobStatus.running]))
    ) or 0
    failed_jobs = db.scalar(
        select(func.count()).select_from(ResearchJob).where(tenant_filter, ResearchJob.status == JobStatus.failed)
    ) or 0
    average_quality_score = db.scalar(
        select(func.avg(ResearchReport.quality_score)).where(ResearchReport.tenant_id == current_user.tenant_id)
    ) or 0
    total_sources = db.scalar(
        select(func.count()).select_from(ResearchSource).where(ResearchSource.tenant_id == current_user.tenant_id)
    ) or 0
    return DashboardStats(
        total_jobs=total_jobs,
        completed_jobs=completed_jobs,
        running_jobs=running_jobs,
        failed_jobs=failed_jobs,
        average_quality_score=round(float(average_quality_score), 1),
        total_sources=total_sources,
    )


@router.get("/{job_id}", response_model=ResearchJobResponse)
def get_research(job_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> ResearchJobResponse:
    return serialize_job(get_tenant_job(db, current_user, job_id))


@router.get("/{job_id}/events", response_model=list[ResearchEventResponse])
def get_events(job_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> list[ResearchEventResponse]:
    get_tenant_job(db, current_user, job_id)
    events = db.scalars(
        select(ResearchEvent)
        .where(ResearchEvent.job_id == job_id, ResearchEvent.tenant_id == current_user.tenant_id)
        .order_by(ResearchEvent.sequence)
    ).all()
    return [
        ResearchEventResponse(
            id=str(event.id),
            sequence=event.sequence,
            event_type=event.event_type,
            agent=event.agent,
            message=event.message,
            payload=event.payload,
            created_at=event.created_at.astimezone(UTC),
        )
        for event in events
    ]


@router.post("/{job_id}/cancel", response_model=ResearchJobResponse)
def cancel_research(job_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> ResearchJobResponse:
    job = get_tenant_job(db, current_user, job_id)
    if current_user.role == UserRole.viewer:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewer role cannot cancel research")
    if current_user.role != UserRole.admin and job.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner or an admin can cancel this job")
    if job.status in {JobStatus.completed, JobStatus.failed, JobStatus.cancelled}:
        return serialize_job(job)
    job.status = JobStatus.cancelled
    job.current_agent = "Cancellation requested"
    task_id = job.config.get("celery_task_id")
    if task_id:
        celery_app.control.revoke(task_id, terminate=False)
    db.commit()
    db.refresh(job)
    EventPublisher(db, job.id, job.tenant_id).publish(
        "cancellation_requested",
        "Research cancellation requested",
        agent="Orchestrator",
    )
    return serialize_job(job)
