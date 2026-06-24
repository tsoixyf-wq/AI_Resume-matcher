"""Resume management API endpoints."""

import os
import time
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.resume import (
    ParsedResumeData,
    ResumeDetailResponse,
    ResumeListResponse,
    ResumeUploadResponse,
)
from app.models.resume import Resume
from app.services.parser.document_loader import DocumentLoader
from app.services.parser.llm_extractor import LLMExtractor
from app.services.parser.ner_extractor import NERExtractor
from app.services.parser.resume_classifier import classify_resume
from app.services.parser.skill_normalizer import SkillNormalizer
from app.utils.file_utils import generate_file_path, validate_file

router = APIRouter()


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload and parse a resume file (PDF/DOCX/TXT)."""
    # Validate file
    content = await file.read()
    is_valid, error_msg = validate_file(file.filename or "unknown", len(content))
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Save file
    file_path = generate_file_path(file.filename or "resume.pdf")
    with open(file_path, "wb") as f:
        f.write(content)

    # Create DB record
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else "txt"
    resume = Resume(
        original_filename=file.filename or "unknown",
        file_path=file_path,
        file_type=ext,
        parse_status="processing",
    )
    db.add(resume)
    await db.flush()

    # Parse resume asynchronously (in real app, this would be a Celery task)
    parsed = ParsedResumeData()  # fallback for error cases
    try:
        start_time = time.time()

        # Load document text
        text = await DocumentLoader.load(file_path)

        # NER extraction
        ner = NERExtractor()
        entities = await ner.extract(text)

        # LLM deep extraction
        llm_extractor = LLMExtractor()
        parsed = await llm_extractor.extract(text)

        # Merge NER results
        if entities.get("email") and not parsed.basic_info.email:
            parsed.basic_info.email = entities["email"]
        if entities.get("phone") and not parsed.basic_info.phone:
            parsed.basic_info.phone = entities["phone"]
        if entities.get("name") and not parsed.basic_info.name:
            parsed.basic_info.name = entities["name"]

        # Normalize skills
        normalizer = SkillNormalizer()
        normalized = normalizer.normalize_list(
            entities.get("skills", []) + [s.name for s in parsed.skills]
        )
        from app.schemas.resume import Skill
        seen_skills = set()
        merged_skills = []
        for s in normalized:
            if s["name"].lower() not in seen_skills:
                seen_skills.add(s["name"].lower())
                merged_skills.append(Skill(
                    name=s["name"],
                    category=s.get("category_display"),
                ))
        parsed.skills = merged_skills

        # Classify resume type (campus vs experienced)
        parsed.resume_type = classify_resume(parsed, text)

        # Update record
        resume.parsed_data = parsed.model_dump()
        resume.raw_text = text
        resume.parse_status = "completed"
        resume.parse_duration_ms = int((time.time() - start_time) * 1000)

    except Exception as e:
        resume.parse_status = "failed"
        resume.parse_error = str(e)

    await db.flush()

    return ResumeUploadResponse(
        id=resume.id,
        original_filename=resume.original_filename,
        file_type=resume.file_type,
        parse_status=resume.parse_status,
        resume_type=parsed.resume_type,
        created_at=resume.created_at,
    )


@router.get("/", response_model=ResumeListResponse)
async def list_resumes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="Filter by parse status"),
    db: AsyncSession = Depends(get_db),
):
    """List all uploaded resumes."""
    query = select(Resume)
    count_query = select(func.count(Resume.id))

    if status:
        query = query.where(Resume.parse_status == status)
        count_query = count_query.where(Resume.parse_status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Resume.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    resumes = result.scalars().all()

    return ResumeListResponse(
        items=[
            ResumeUploadResponse(
                id=r.id,
                original_filename=r.original_filename,
                file_type=r.file_type,
                parse_status=r.parse_status,
                resume_type=(r.parsed_data or {}).get("resume_type", "unknown"),
                created_at=r.created_at,
            )
            for r in resumes
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{resume_id}", response_model=ResumeDetailResponse)
async def get_resume(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed resume information."""
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")

    return ResumeDetailResponse(
        id=resume.id,
        original_filename=resume.original_filename,
        file_type=resume.file_type,
        parsed_data=ParsedResumeData(**resume.parsed_data),
        raw_text=resume.raw_text,
        parse_status=resume.parse_status,
        parse_error=resume.parse_error,
        parse_duration_ms=resume.parse_duration_ms,
        created_at=resume.created_at,
    )


@router.delete("/{resume_id}")
async def delete_resume(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a resume."""
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")

    # Delete file
    if os.path.exists(resume.file_path):
        os.remove(resume.file_path)

    await db.delete(resume)
    return {"detail": "删除成功"}
