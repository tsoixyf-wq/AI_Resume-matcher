"""Reports API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.job import JobDescription
from app.models.match_result import MatchResult
from app.models.resume import Resume

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_data(
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard summary statistics.

    All aggregations are pushed down to the database to avoid loading
    full tables into memory and to eliminate N+1 queries on top matches.
    """
    # --- Total counts (single-row scalar per table) ---
    total_resumes = (await db.execute(select(func.count(Resume.id)))).scalar() or 0
    total_jobs = (await db.execute(select(func.count(JobDescription.id)))).scalar() or 0
    total_matches = (await db.execute(select(func.count(MatchResult.id)))).scalar() or 0

    # --- Parse status breakdown via GROUP BY ---
    parse_status_rows = await db.execute(
        select(Resume.parse_status, func.count())
        .group_by(Resume.parse_status)
    )
    parse_status = {"pending": 0, "processing": 0, "completed": 0, "failed": 0}
    for status, cnt in parse_status_rows.all():
        if status in parse_status:
            parse_status[status] = cnt

    # --- Score distribution via CASE expression + GROUP BY ---
    score_bucket = case(
        (MatchResult.overall_score <= 3, "0-3"),
        (MatchResult.overall_score <= 5, "4-5"),
        (MatchResult.overall_score <= 7, "6-7"),
        else_="8-10",
    )
    score_rows = await db.execute(
        select(score_bucket.label("bucket"), func.count())
        .group_by(score_bucket)
    )
    score_distribution = {"0-3": 0, "4-5": 0, "6-7": 0, "8-10": 0}
    for bucket, cnt in score_rows.all():
        score_distribution[bucket] = cnt

    # --- Average score ---
    avg_score = round(
        (await db.execute(select(func.avg(MatchResult.overall_score)))).scalar() or 0,
        1,
    )

    # --- Top 5 matches with resume/job names via JOIN (no N+1) ---
    top_rows = await db.execute(
        select(
            MatchResult.id,
            MatchResult.overall_score,
            MatchResult.created_at,
            Resume.original_filename,
            JobDescription.title,
        )
        .join(Resume, Resume.id == MatchResult.resume_id, isouter=True)
        .join(JobDescription, JobDescription.id == MatchResult.job_id, isouter=True)
        .order_by(desc(MatchResult.overall_score))
        .limit(5)
    )
    top_matches = [
        {
            "match_id": str(row.id),
            "resume_name": row.original_filename or "unknown",
            "job_title": row.title or "unknown",
            "score": row.overall_score,
            "date": row.created_at.isoformat() if row.created_at else "",
        }
        for row in top_rows.all()
    ]

    return {
        "total_resumes": total_resumes,
        "total_jobs": total_jobs,
        "total_matches": total_matches,
        "parse_status": parse_status,
        "score_distribution": score_distribution,
        "top_matches": top_matches,
        "avg_score": avg_score,
    }
