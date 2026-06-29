"""Async Celery tasks for resume parsing, batch matching, and cleanup.

Each task runs in its own process via Celery.  Async database and
LLM calls are wrapped with asyncio.run() inside the sync task body.
"""

import asyncio
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.resume import Resume
from app.services.parser.document_loader import DocumentLoader
from app.services.parser.service import ResumeParserService
from app.tasks.celery_app import celery_app
from app.utils.storage import get_storage

logger = logging.getLogger(__name__)

# Max concurrent matcher executions in batch matching (CPU/GPU-bound work)
_BATCH_MATCH_CONCURRENCY = 4

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_async(coro):
    """Run an async coroutine inside a sync Celery task."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Task: parse_resume_async
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="parse_resume_async", max_retries=2)
def parse_resume_async(self, resume_id: str):
    """Parse a single resume asynchronously.

    Called by the upload API after the DB record is created.
    Updates the resume record with parsed data and status.
    """
    logger.info("parse_resume_async started, resume_id=%s", resume_id)
    return _run_async(_do_parse_resume(resume_id, task_id=self.request.id))


async def _do_parse_resume(resume_id: str, task_id: str = "") -> dict:
    async with async_session_factory() as db:
        result = await db.execute(
            select(Resume).where(Resume.id == uuid.UUID(resume_id))
        )
        resume = result.scalar_one_or_none()
        if not resume:
            return {"resume_id": resume_id, "status": "not_found"}

        try:
            resume.parse_status = "processing"
            await db.flush()

            text = await DocumentLoader.load(resume.file_path)

            # Parse via shared service (NER → LLM → merge → normalize → classify)
            service = ResumeParserService()
            parse_result = await service.parse(text)
            parsed = parse_result.parsed

            if parse_result.llm_error:
                resume.parse_error = f"LLM skipped: {parse_result.llm_error}"

            resume.parsed_data = parsed.model_dump()
            resume.raw_text = text
            resume.parse_status = "completed"
            resume.parse_duration_ms = parse_result.duration_ms

            # Create embedding for similarity search
            try:
                from app.services.embedding.embedding_service import embed_resume
                embedding_id = await embed_resume(
                    resume_id, text,
                    metadata={"filename": resume.original_filename, "type": resume.file_type},
                )
                resume.embedding_id = embedding_id
            except Exception as emb_err:
                logger.warning("Embedding failed (non-critical): %s", emb_err)

            logger.info(
                "parse_resume_async completed, resume_id=%s, type=%s",
                resume_id,
                parsed.resume_type,
            )

        except Exception as exc:
            resume.parse_status = "failed"
            resume.parse_error = str(exc)[:500]
            logger.exception("parse_resume_async failed, resume_id=%s", resume_id)
            return {"resume_id": resume_id, "status": "failed", "error": str(exc)[:200]}

        await db.commit()

    return {"resume_id": resume_id, "status": "completed"}


# ---------------------------------------------------------------------------
# Task: batch_match_async
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="batch_match_async")
def batch_match_async(self, resume_ids: list[str], job_id: str, enable_llm: bool = False):
    """Batch match multiple resumes against a single job.

    Args:
        resume_ids: list of resume UUID strings
        job_id: job description UUID string
        enable_llm: whether to run LLM stage (expensive)

    Updates task state with progress: {current, total, results: [...]}
    """
    logger.info("batch_match_async started, count=%d, job_id=%s", len(resume_ids), job_id)
    return _run_async(_do_batch_match(
        resume_ids, job_id, enable_llm,
        on_progress=lambda c, t, r: self.update_state(
            state="PROGRESS",
            meta={"current": c, "total": t, "results": r},
        ),
    ))


async def _do_batch_match(
    resume_ids: list[str],
    job_id: str,
    enable_llm: bool,
    on_progress=None,
) -> dict:
    # Heavy matcher imports kept lazy to avoid loading ML models at worker startup
    from app.models.job import JobDescription
    from app.models.match_result import MatchResult
    from app.schemas.job import ParsedJDData
    from app.schemas.matching import DimensionScores
    from app.schemas.resume import ParsedResumeData
    from app.services.matcher.llm_matcher import LLMMatcher
    from app.services.matcher.rule_matcher import RuleMatcher
    from app.services.matcher.semantic_matcher import SemanticMatcher
    from app.services.matcher.tfidf_matcher import TFIDFMatcher
    from app.services.matcher.weighting import compute_weighted_score

    # Limit concurrent matcher executions to avoid overwhelming CPU/GPU
    sem = asyncio.Semaphore(_BATCH_MATCH_CONCURRENCY)

    async def _match_one(resume_data: ParsedResumeData, jd_data: ParsedJDData):
        """Run matchers for a single resume (no DB access). Returns a dict of match fields."""
        async with sem:
            rule = await RuleMatcher().match(resume_data, jd_data)
            if rule.get("is_hard_pass"):
                return {
                    "is_hard_pass": True,
                    "rule_score": rule["score"],
                    "hard_pass_reasons": rule.get("hard_pass_reasons", []),
                }

            tfidf = await TFIDFMatcher().match(resume_data, jd_data)
            semantic = await SemanticMatcher().match(resume_data, jd_data)

            llm_res = None
            if enable_llm:
                llm_res = await LLMMatcher().match(resume_data, jd_data, {
                    "rule": rule["score"], "tfidf": tfidf["score"], "semantic": semantic["score"],
                })

            overall, dim_scores, _ = compute_weighted_score(
                rule_score=rule["score"],
                tfidf_score=tfidf["score"],
                semantic_score=semantic["score"],
                llm_result=llm_res,
            )

            return {
                "is_hard_pass": False,
                "rule_score": rule["score"],
                "tfidf_score": tfidf["score"],
                "semantic_score": semantic["score"],
                "llm_score": llm_res["score"] if llm_res else None,
                "overall_score": round(overall, 1),
                "dimension_scores": dim_scores.model_dump(),
                "matched_skills": llm_res.get("matched_skills", []) if llm_res else [],
                "missing_skills": llm_res.get("missing_skills", []) if llm_res else [],
                "llm_reasoning": llm_res.get("reasoning", "") if llm_res else None,
                "suggestions": llm_res.get("suggestions", []) if llm_res else [],
            }

    async with async_session_factory() as db:
        jd_result = await db.execute(
            select(JobDescription).where(JobDescription.id == uuid.UUID(job_id))
        )
        jd = jd_result.scalar_one_or_none()
        if not jd:
            return {"error": f"Job {job_id} not found"}

        jd_data = ParsedJDData(**jd.parsed_data)

        # Batch-load all resumes in a single query (avoids N round-trips)
        resume_rows = await db.execute(
            select(Resume).where(Resume.id.in_([uuid.UUID(rid) for rid in resume_ids]))
        )
        resume_map = {str(r.id): r for r in resume_rows.scalars().all()}

        # Separate completed resumes from skipped ones; preserve input order
        to_match: list[tuple[str, ParsedResumeData]] = []
        results: list[dict] = [None] * len(resume_ids)  # type: ignore[list-item]
        for i, rid_str in enumerate(resume_ids):
            resume = resume_map.get(rid_str)
            if not resume or resume.parse_status != "completed":
                results[i] = {"resume_id": rid_str, "status": "skipped"}
            else:
                try:
                    resume_data = ParsedResumeData(**resume.parsed_data)
                except Exception:
                    logger.exception("Batch match: invalid parsed_data for resume %s", rid_str)
                    results[i] = {"resume_id": rid_str, "status": "failed",
                                  "error": "invalid parsed_data"}
                else:
                    to_match.append((rid_str, resume_data))

        # Run matchers concurrently; collect results as they complete
        pending: dict[asyncio.Future, str] = {}
        for rid_str, resume_data in to_match:
            task = asyncio.create_task(_match_one(resume_data, jd_data))
            pending[task] = rid_str

        completed_count = len(resume_ids) - len(to_match)  # already-resolved (skipped/failed)
        # Report initial progress for skipped items
        if on_progress and completed_count > 0:
            on_progress(completed_count, len(resume_ids), [r for r in results if r])

        for done in asyncio.as_completed(pending):
            rid_str = pending[done]
            idx = resume_ids.index(rid_str)
            try:
                match_data = await done
                if match_data.get("is_hard_pass"):
                    mr = MatchResult(
                        resume_id=uuid.UUID(rid_str), job_id=uuid.UUID(job_id),
                        rule_score=match_data["rule_score"], overall_score=0.0,
                        dimension_scores=DimensionScores().model_dump(),
                        hard_pass_reasons=match_data.get("hard_pass_reasons", []),
                        is_hard_pass=True,
                    )
                    db.add(mr)
                    await db.flush()
                    results[idx] = {"resume_id": rid_str, "overall_score": 0.0,
                                    "is_hard_pass": True}
                else:
                    mr = MatchResult(
                        resume_id=uuid.UUID(rid_str), job_id=uuid.UUID(job_id),
                        rule_score=match_data["rule_score"],
                        tfidf_score=match_data["tfidf_score"],
                        semantic_score=match_data["semantic_score"],
                        llm_score=match_data["llm_score"],
                        overall_score=match_data["overall_score"],
                        dimension_scores=match_data["dimension_scores"],
                        matched_skills=match_data["matched_skills"],
                        missing_skills=match_data["missing_skills"],
                        llm_reasoning=match_data["llm_reasoning"],
                        suggestions=match_data["suggestions"],
                    )
                    db.add(mr)
                    await db.flush()
                    results[idx] = {"resume_id": rid_str,
                                    "overall_score": match_data["overall_score"],
                                    "match_result_id": str(mr.id)}
            except Exception as exc:
                logger.exception("Batch match failed for resume %s", rid_str)
                results[idx] = {"resume_id": rid_str, "status": "failed",
                                "error": str(exc)[:200]}

            completed_count += 1
            if on_progress:
                on_progress(completed_count, len(resume_ids),
                            [r for r in results if r])

        await db.commit()

    return {
        "completed": len([
            r for r in results
            if r and (r.get("overall_score") is not None or r.get("is_hard_pass"))
        ]),
        "total": len(resume_ids),
        "results": results,
    }


# ---------------------------------------------------------------------------
# Task: cleanup_old_files
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="cleanup_old_files")
def cleanup_old_files(self, days: int = 30):
    """Remove temp files and failed parse records older than *days*."""
    logger.info("cleanup_old_files started, days=%d", days)
    return _run_async(_do_cleanup(days))


async def _do_cleanup(days: int) -> dict:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    deleted_files = 0
    deleted_records = 0

    async with async_session_factory() as db:
        # Find old failed / pending records
        result = await db.execute(
            select(Resume).where(
                Resume.parse_status.in_(["failed", "pending"]),
                Resume.created_at < cutoff,
            )
        )
        stale = result.scalars().all()

        storage = get_storage()
        for r in stale:
            # Delete from MinIO if applicable
            if r.file_path.startswith("resumes/"):
                try:
                    await storage.delete(r.file_path)
                    deleted_files += 1
                except Exception:
                    pass
            # Also delete local file if it exists
            if os.path.exists(r.file_path):
                try:
                    os.remove(r.file_path)
                    deleted_files += 1
                except OSError:
                    pass
            await db.delete(r)
            deleted_records += 1

        await db.commit()

    logger.info(
        "cleanup_old_files done: %d files, %d records deleted",
        deleted_files,
        deleted_records,
    )
    return {"deleted_files": deleted_files, "deleted_records": deleted_records, "days": days}
