"""Resume management API endpoints."""

import logging
import os
import tempfile
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_api_key
from app.models.resume import Resume
from app.schemas.resume import (
    ParsedResumeData,
    ResumeDetailResponse,
    ResumeListResponse,
    ResumeUploadResponse,
)
from app.services.parser.document_loader import DocumentLoader
from app.utils.file_utils import generate_file_path, validate_file
from app.utils.storage import get_storage

logger = logging.getLogger(__name__)
router = APIRouter()


def _object_name(resume_id: uuid.UUID, original_filename: str) -> str:
    """Build a deterministic MinIO object name from resume id + extension."""
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "txt"
    return f"resumes/{resume_id}.{ext}"


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    """Upload and parse a resume file (PDF/DOCX/TXT).

    - DEV mode (DEBUG=true): parses synchronously inline
    - Production mode (DEBUG=false): dispatches to Celery worker
    """
    from app.core.config import get_settings
    settings = get_settings()

    # Validate file
    content = await file.read()
    is_valid, error_msg = validate_file(file.filename or "unknown", len(content))
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Save file to local temp path (needed for parsing)
    file_path = generate_file_path(file.filename or "resume.pdf")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)

    # Create DB record
    ext = (
        file.filename.rsplit(".", 1)[-1].lower()
        if file.filename and "." in file.filename
        else "txt"
    )
    resume = Resume(
        original_filename=file.filename or "unknown",
        file_path=file_path,
        file_type=ext,
        parse_status="processing",
    )
    db.add(resume)
    await db.flush()

    # --- Production: dispatch to Celery ---
    if not settings.DEBUG:
        from app.tasks.matching_tasks import parse_resume_async
        parse_resume_async.delay(str(resume.id))
        return ResumeUploadResponse(
            id=resume.id,
            original_filename=resume.original_filename,
            file_type=resume.file_type,
            parse_status="processing",
            resume_type="unknown",
            created_at=resume.created_at,
        )

    # --- Dev mode: parse synchronously ---
    try:
        from app.services.parser.service import ResumeParserService

        # Load document text
        text = await DocumentLoader.load(file_path)

        # Parse via shared service (NER → LLM → merge → normalize → classify)
        service = ResumeParserService()
        result = await service.parse(text)
        parsed = result.parsed

        if result.llm_error:
            resume.parse_error = f"LLM skipped: {result.llm_error}"

        # Update record
        resume.parsed_data = parsed.model_dump()
        resume.raw_text = text
        resume.parse_status = "completed"
        resume.parse_duration_ms = result.duration_ms

        # --- Upload to MinIO (if configured) ---
        storage = get_storage()
        await storage.ensure_bucket()
        obj_name = _object_name(resume.id, resume.original_filename)
        await storage.upload(file_path, obj_name)
        resume.file_path = obj_name

        # --- Create embedding for similarity search ---
        try:
            from app.services.embedding.embedding_service import embed_resume
            embedding_id = await embed_resume(
                str(resume.id), text,
                metadata={"filename": resume.original_filename, "type": resume.file_type},
            )
            resume.embedding_id = embedding_id
        except Exception as emb_err:
            logger.warning("Embedding failed (non-critical): %s", emb_err)

    except Exception as e:
        logger.exception("Resume parsing failed, removing record: %s", resume.id)
        # Delete the failed DB record — no value in keeping it in the list
        await db.delete(resume)
        await db.flush()
        # Clean up local temp file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass
        raise HTTPException(
            status_code=422,
            detail=f"简历解析失败: {str(e)[:300]}",
        )

    # Clean up local temp file (success path)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except OSError:
        pass

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

    # 默认排除失败记录——解析失败时已通过 API 错误提示，列表中无意义
    query = query.where(Resume.parse_status != "failed")
    count_query = count_query.where(Resume.parse_status != "failed")

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


@router.get("/{resume_id}/download")
async def download_resume(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Download the original resume file."""
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")

    storage = get_storage()
    path = resume.file_path

    # If stored in MinIO (object name starts with "resumes/"), download to temp
    if storage.enabled and path.startswith("resumes/"):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{resume.file_type}")
        try:
            await storage.download(path, tmp.name)
            return FileResponse(
                tmp.name,
                filename=resume.original_filename,
                media_type="application/octet-stream",
            )
        except Exception:
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)
            raise HTTPException(status_code=500, detail="文件下载失败")

    # Fallback: local file path
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"文件不存在: {path}")

    return FileResponse(
        path,
        filename=resume.original_filename,
        media_type="application/octet-stream",
    )


@router.delete("/{resume_id}")
async def delete_resume(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    """Delete a resume and its file."""
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")

    storage = get_storage()

    # Delete file from MinIO (if object name looks like a MinIO key)
    if storage.enabled and resume.file_path.startswith("resumes/"):
        try:
            await storage.delete(resume.file_path)
        except Exception:
            pass  # best-effort cleanup

    # Also delete local file if it exists (dev mode or legacy record)
    if os.path.exists(resume.file_path):
        try:
            os.remove(resume.file_path)
        except OSError:
            pass

    # Delete embedding
    try:
        from app.services.embedding.embedding_service import delete_resume_embedding
        await delete_resume_embedding(str(resume_id))
    except Exception:
        pass

    # Cascade delete match results associated with this resume
    from sqlalchemy import delete as sqla_delete

    from app.models.match_result import MatchResult
    await db.execute(sqla_delete(MatchResult).where(MatchResult.resume_id == resume_id))

    await db.delete(resume)
    return {"detail": "删除成功"}
