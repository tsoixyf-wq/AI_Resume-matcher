"""Pydantic schemas for Matching results."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DimensionScores(BaseModel):
    """Scores for each matching dimension (7 dimensions)."""
    education: float = Field(default=0.0, description="学历匹配得分 (0-10)")
    skills: float = Field(default=0.0, description="技能匹配得分 (0-10)")
    experience: float = Field(default=0.0, description="经验匹配得分 (0-10)")
    certifications: float = Field(default=0.0, description="证书匹配得分 (0-10)")
    languages: float = Field(default=0.0, description="语言能力得分 (0-10)")
    location: float = Field(default=0.0, description="地点匹配得分 (0-10)")
    overall: float = Field(default=0.0, description="综合得分 (0-10)")


class MatchRequest(BaseModel):
    """Request to match a resume against a job description."""
    resume_id: uuid.UUID
    job_id: uuid.UUID
    enable_llm: bool = Field(default=True, description="是否启用 LLM 深度推理")
    enable_stream: bool = Field(default=False, description="是否流式返回 LLM 分析过程")


class MatchResponse(BaseModel):
    id: uuid.UUID
    resume_id: uuid.UUID
    job_id: uuid.UUID

    # Scores
    rule_score: float | None = None
    tfidf_score: float | None = None
    semantic_score: float | None = None
    llm_score: float | None = None
    overall_score: float

    # Details
    dimension_scores: DimensionScores
    matched_skills: list[str]
    missing_skills: list[str]
    llm_reasoning: str | None = None
    suggestions: list[str]

    # Hard filters
    is_hard_pass: bool
    hard_pass_reasons: list[str]

    # Meta
    match_duration_ms: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BatchMatchRequest(BaseModel):
    """Request to batch-match multiple resumes against one job."""
    resume_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=100)
    job_id: uuid.UUID
    enable_llm: bool = Field(default=False, description="批量模式下默认不启用 LLM 以节约成本")


class BatchMatchResponse(BaseModel):
    matches: list[MatchResponse]
    total: int
    completed: int
    failed: int
