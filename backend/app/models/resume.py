"""Resume ORM model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.match_result import MatchResult


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)

    # Parsed structured data
    parsed_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Metadata
    parse_status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, processing, completed, failed
    parse_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parse_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Embedding
    embedding_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    match_results: Mapped[list["MatchResult"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )
