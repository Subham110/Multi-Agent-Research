import uuid
from datetime import UTC, datetime

import structlog
from celery import shared_task
from sqlalchemy import delete

from app.agents.graph import ResearchCancelled, ResearchWorkflow
from app.db.models import JobStatus, ResearchJob, ResearchReport, ResearchSource
from app.db.session import SessionLocal
from app.services.event_bus import EventPublisher
from app.services.gemini import GeminiService
from app.services.memory import MemoryService

logger = structlog.get_logger()


@shared_task(bind=True, autoretry_for=(ConnectionError,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def run_research_job(self, job_id: str) -> dict:
    db = SessionLocal()
    job_uuid = uuid.UUID(job_id)
    try:
        job = db.get(ResearchJob, job_uuid)
        if not job:
            return {"status": "missing", "job_id": job_id}
        if job.status == JobStatus.completed:
            return {"status": "already_completed", "job_id": job_id}
        if job.status == JobStatus.cancelled:
            return {"status": "cancelled_before_start", "job_id": job_id}

        EventPublisher.ensure_sequence(db, job.id)
        job.status = JobStatus.running
        job.started_at = job.started_at or datetime.now(UTC)
        job.error = None
        db.commit()

        state = ResearchWorkflow(db, job).run()
        db.refresh(job)
        if job.status == JobStatus.cancelled:
            raise ResearchCancelled("Research job was cancelled before persistence")
        final = state["final_report"]
        registry = state["source_registry"]

        # Retry-safe persistence: replace derived records for this job atomically.
        db.execute(delete(ResearchSource).where(ResearchSource.job_id == job.id))
        for source in registry:
            db.add(
                ResearchSource(
                    tenant_id=job.tenant_id,
                    job_id=job.id,
                    title=source.get("title", "Source"),
                    url=source["url"],
                    source_type=source.get("source_type", "web"),
                    authors=source.get("authors", []),
                    published_at=source.get("published_at"),
                    abstract=" ".join(source.get("key_points", []))[:5000],
                    excerpt=" ".join(source.get("key_points", []))[:2000],
                    credibility_score=float(source.get("credibility_score", 0.5)),
                )
            )

        report = job.report or ResearchReport(tenant_id=job.tenant_id, job_id=job.id)
        report.title = final["title"]
        report.executive_summary = final["executive_summary"]
        report.markdown = final["markdown"]
        report.quality_score = final["quality_score"]
        report.citation_count = len(final["citation_keys"])
        report.metadata_json = {
            "citation_keys": final["citation_keys"],
            "agent_iterations": {
                "researcher": state.get("research_iteration", 0),
                "analyst": state.get("analysis_iteration", 0),
                "writer": state.get("writer_iteration", 0),
                "critic": state.get("critic_iteration", 0),
                "revisions": state.get("revision_iteration", 0),
            },
        }
        db.add(report)
        job.status = JobStatus.completed
        job.current_agent = "Complete"
        job.progress = 100
        job.completed_at = datetime.now(UTC)
        db.add(job)
        db.commit()
        EventPublisher(db, job.id, job.tenant_id).publish(
            "job_completed",
            f"Research report completed with quality score {report.quality_score}",
            agent="Orchestrator",
            payload={
                "quality_score": report.quality_score,
                "citation_count": report.citation_count,
            },
        )

        try:
            memory = MemoryService(db, GeminiService())
            memory.remember_report(
                job.tenant_id,
                job.id,
                report.markdown,
                {"topic": job.topic, "quality_score": report.quality_score},
            )
        except Exception as memory_error:
            logger.warning("report_memory_failed", job_id=job_id, error=str(memory_error))

        return {"status": "completed", "job_id": job_id, "quality_score": report.quality_score}
    except ResearchCancelled:
        db.rollback()
        job = db.get(ResearchJob, job_uuid)
        if job:
            job.status = JobStatus.cancelled
            job.current_agent = "Cancelled"
            job.completed_at = datetime.now(UTC)
            db.add(job)
            db.commit()
            EventPublisher(db, job.id, job.tenant_id).publish(
                "job_cancelled", "Research workflow cancelled", agent="Orchestrator"
            )
        return {"status": "cancelled", "job_id": job_id}
    except Exception as exc:
        db.rollback()
        job = db.get(ResearchJob, job_uuid)
        if job:
            job.status = JobStatus.failed
            job.error = str(exc)[:4000]
            job.completed_at = datetime.now(UTC)
            db.add(job)
            db.commit()
            try:
                EventPublisher(db, job.id, job.tenant_id).publish(
                    "job_failed", "Research workflow failed", agent="Orchestrator", payload={"error": str(exc)[:1000]}
                )
            except Exception:
                logger.exception("failed_to_publish_failure_event", job_id=job_id)
        logger.exception("research_job_failed", job_id=job_id)
        raise
    finally:
        db.close()
