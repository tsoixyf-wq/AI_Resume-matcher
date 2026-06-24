"""Matching API endpoints."""

import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.job import JobDescription
from app.models.match_result import MatchResult
from app.models.resume import Resume
from app.schemas.job import ParsedJDData
from app.schemas.matching import (
    BatchMatchRequest,
    BatchMatchResponse,
    DimensionScores,
    MatchRequest,
    MatchResponse,
)
from app.schemas.resume import ParsedResumeData
from app.services.matcher.llm_matcher import LLMMatcher
from app.services.matcher.rule_matcher import RuleMatcher
from app.services.matcher.semantic_matcher import SemanticMatcher
from app.services.matcher.tfidf_matcher import TFIDFMatcher
from app.services.matcher.weighting import compute_weighted_score

router = APIRouter()


@router.post("/analyze", response_model=MatchResponse)
async def match_resume_to_job(
    request: MatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run the full matching pipeline for a resume against a job."""
    start_time = time.time()

    # Load resume
    resume_result = await db.execute(select(Resume).where(Resume.id == request.resume_id))
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    if resume.parse_status != "completed":
        raise HTTPException(status_code=400, detail="简历尚未解析完成")

    # Load JD
    jd_result = await db.execute(select(JobDescription).where(JobDescription.id == request.job_id))
    jd = jd_result.scalar_one_or_none()
    if not jd:
        raise HTTPException(status_code=404, detail="岗位不存在")

    resume_data = ParsedResumeData(**resume.parsed_data)
    jd_data = ParsedJDData(**jd.parsed_data)

    # Stage 1: Rule matching
    rule_matcher = RuleMatcher()
    rule_result = await rule_matcher.match(resume_data, jd_data)

    if rule_result["is_hard_pass"]:
        # Extract missing hard-requirement skills from rule check details
        rule_missing_skills = (
            rule_result.get("details", {}).get("skills", {}).get("missing", [])
        )
        # Also include hard-pass reasons as context for the frontend
        hard_pass_skill_items = [
            f"❌ {reason}" for reason in rule_result["hard_pass_reasons"]
        ] + [f"⚠️ 缺少必备技能: {s}" for s in rule_missing_skills]

        # Create result and return early
        match_result = MatchResult(
            resume_id=request.resume_id,
            job_id=request.job_id,
            rule_score=rule_result["score"],
            overall_score=0.0,
            dimension_scores=DimensionScores().model_dump(),
            matched_skills=[],
            missing_skills=hard_pass_skill_items,
            hard_pass_reasons=rule_result["hard_pass_reasons"],
            is_hard_pass=True,
            match_duration_ms=int((time.time() - start_time) * 1000),
        )
        db.add(match_result)
        await db.flush()
        return _build_match_response(match_result)

    # Stage 2: TF-IDF
    tfidf_matcher = TFIDFMatcher()
    tfidf_result = await tfidf_matcher.match(resume_data, jd_data)

    # Stage 3: Semantic
    semantic_matcher = SemanticMatcher()
    semantic_result = await semantic_matcher.match(resume_data, jd_data)

    # Stage 4: LLM (optional)
    llm_result = None
    if request.enable_llm:
        llm_matcher = LLMMatcher()
        previous = {
            "rule": rule_result["score"],
            "tfidf": tfidf_result["score"],
            "semantic": semantic_result["score"],
        }
        llm_result = await llm_matcher.match(resume_data, jd_data, previous)

    # Weighted aggregation — centralized in weighting.py
    overall, dim_scores, _ = compute_weighted_score(
        rule_score=rule_result["score"],
        tfidf_score=tfidf_result["score"],
        semantic_score=semantic_result["score"],
        llm_result=llm_result,
    )

    # Persist result
    match_result = MatchResult(
        resume_id=request.resume_id,
        job_id=request.job_id,
        rule_score=rule_result["score"],
        tfidf_score=tfidf_result["score"],
        semantic_score=semantic_result["score"],
        llm_score=llm_result["score"] if llm_result else None,
        overall_score=round(overall, 1),
        dimension_scores=dim_scores.model_dump(),
        matched_skills=llm_result.get("matched_skills", []) if llm_result else [],
        missing_skills=llm_result.get("missing_skills", []) if llm_result else [],
        llm_reasoning=llm_result.get("reasoning", "") if llm_result else None,
        suggestions=llm_result.get("suggestions", []) if llm_result else [],
        match_duration_ms=int((time.time() - start_time) * 1000),
    )
    db.add(match_result)
    await db.flush()

    return _build_match_response(match_result)


@router.post("/analyze/stream")
async def match_resume_stream(
    request: MatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Stream the LLM matching analysis in real time (SSE)."""
    # Load resume and JD
    resume_result = await db.execute(select(Resume).where(Resume.id == request.resume_id))
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")

    jd_result = await db.execute(select(JobDescription).where(JobDescription.id == request.job_id))
    jd = jd_result.scalar_one_or_none()
    if not jd:
        raise HTTPException(status_code=404, detail="岗位不存在")

    resume_data = ParsedResumeData(**resume.parsed_data)
    jd_data = ParsedJDData(**jd.parsed_data)

    llm_matcher = LLMMatcher()

    async def generate():
        yield "data: {\"status\": \"started\"}\n\n"
        async for token in llm_matcher.match_stream(resume_data, jd_data):
            yield f"data: {{\"token\": {__import__('json').dumps(token)}}}\n\n"
        yield "data: {\"status\": \"completed\"}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/analyze/batch", response_model=BatchMatchResponse)
async def batch_match(
    request: BatchMatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Batch match multiple resumes against one job."""
    matches = []
    failed = 0

    for resume_id in request.resume_ids:
        try:
            single_request = MatchRequest(
                resume_id=resume_id,
                job_id=request.job_id,
                enable_llm=request.enable_llm,
            )
            result = await match_resume_to_job(single_request, db)
            matches.append(result)
        except Exception:
            failed += 1

    return BatchMatchResponse(
        matches=matches,
        total=len(request.resume_ids),
        completed=len(matches),
        failed=failed,
    )


@router.get("/results/{match_id}", response_model=MatchResponse)
async def get_match_result(
    match_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific match result."""
    result = await db.execute(select(MatchResult).where(MatchResult.id == match_id))
    match = result.scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=404, detail="匹配结果不存在")

    return _build_match_response(match)


@router.get("/results/")
async def list_match_results(
    resume_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List match results, optionally filtered by resume or job."""
    query = select(MatchResult).order_by(MatchResult.overall_score.desc())

    if resume_id:
        query = query.where(MatchResult.resume_id == resume_id)
    if job_id:
        query = query.where(MatchResult.job_id == job_id)

    result = await db.execute(query.limit(50))
    matches = result.scalars().all()

    return {"items": [_build_match_response(m) for m in matches], "total": len(matches)}


def _build_match_response(match: MatchResult) -> MatchResponse:
    """Convert ORM model to response schema."""
    return MatchResponse(
        id=match.id,
        resume_id=match.resume_id,
        job_id=match.job_id,
        rule_score=match.rule_score,
        tfidf_score=match.tfidf_score,
        semantic_score=match.semantic_score,
        llm_score=match.llm_score,
        overall_score=match.overall_score,
        dimension_scores=DimensionScores(**match.dimension_scores),
        matched_skills=match.matched_skills,
        missing_skills=match.missing_skills,
        llm_reasoning=match.llm_reasoning,
        suggestions=match.suggestions,
        is_hard_pass=match.is_hard_pass,
        hard_pass_reasons=match.hard_pass_reasons,
        match_duration_ms=match.match_duration_ms,
        created_at=match.created_at,
    )
