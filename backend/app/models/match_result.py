"""Match Result ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MatchResult(Base):
    __tablename__ = "match_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # Multi-stage scores
    rule_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    tfidf_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    semantic_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    llm_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Detailed analysis
    dimension_scores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    matched_skills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    missing_skills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    llm_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggestions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Hard filters
    is_hard_pass: Mapped[bool] = mapped_column(default=False)
    hard_pass_reasons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Metadata
    match_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
