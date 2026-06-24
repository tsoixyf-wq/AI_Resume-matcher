"""Reports API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.match_result import MatchResult
from app.models.resume import Resume
from app.models.job import JobDescription

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_data(
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard summary statistics."""
    # Total counts
    resumes_result = await db.execute(select(Resume))
    resumes = resumes_result.scalars().all()

    jds_result = await db.execute(select(JobDescription))
    jds = jds_result.scalars().all()

    matches_result = await db.execute(select(MatchResult))
    matches = matches_result.scalars().all()

    # Parse status breakdown
    parse_status = {"pending": 0, "processing": 0, "completed": 0, "failed": 0}
    for r in resumes:
        status = r.parse_status
        if status in parse_status:
            parse_status[status] += 1

    # Score distribution
    score_distribution = {"0-3": 0, "4-5": 0, "6-7": 0, "8-10": 0}
    for m in matches:
        score = m.overall_score
        if score <= 3:
            score_distribution["0-3"] += 1
        elif score <= 5:
            score_distribution["4-5"] += 1
        elif score <= 7:
            score_distribution["6-7"] += 1
        else:
            score_distribution["8-10"] += 1

    # Top matches
    top_matches = sorted(matches, key=lambda m: m.overall_score, reverse=True)[:5]
    top_items = []
    for m in top_matches:
        resume_result = await db.execute(select(Resume).where(Resume.id == m.resume_id))
        resume = resume_result.scalar_one_or_none()
        jd_result = await db.execute(select(JobDescription).where(JobDescription.id == m.job_id))
        jd = jd_result.scalar_one_or_none()

        top_items.append({
            "match_id": str(m.id),
            "resume_name": resume.original_filename if resume else "unknown",
            "job_title": jd.title if jd else "unknown",
            "score": m.overall_score,
            "date": m.created_at.isoformat() if m.created_at else "",
        })

    return {
        "total_resumes": len(resumes),
        "total_jobs": len(jds),
        "total_matches": len(matches),
        "parse_status": parse_status,
        "score_distribution": score_distribution,
        "top_matches": top_items,
        "avg_score": round(sum(m.overall_score for m in matches) / len(matches), 1) if matches else 0,
    }
