"""Async Celery tasks for batch resume processing and matching."""

import uuid

import structlog

from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, name="parse_resume_async")
def parse_resume_async(self, resume_id: str):
    """Asynchronously parse a single resume."""
    logger.info("Async resume parsing started", resume_id=resume_id)
    # In a real app, this would call the parsing pipeline
    # For now, it's a placeholder for the Celery worker
    return {"resume_id": resume_id, "status": "completed"}


@celery_app.task(bind=True, name="batch_match_async")
def batch_match_async(self, resume_ids: list[str], job_id: str):
    """Asynchronously batch-match multiple resumes against a job."""
    logger.info("Batch matching started", count=len(resume_ids), job_id=job_id)

    results = []
    for i, rid in enumerate(resume_ids):
        self.update_state(
            state="PROGRESS",
            meta={"current": i + 1, "total": len(resume_ids)},
        )
        # In a real app, this would call the matching pipeline
        results.append({"resume_id": rid, "job_id": job_id, "status": "matched"})

    return {"completed": len(results), "total": len(resume_ids)}


@celery_app.task(bind=True, name="cleanup_old_files")
def cleanup_old_files(self, days: int = 30):
    """Clean up old resume files and records."""
    logger.info("Cleanup task started", days=days)
    # Placeholder for cleanup logic
    return {"deleted": 0, "days": days}
