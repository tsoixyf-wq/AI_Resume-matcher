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
    """Complete match result returned by the matching pipeline."""

    id: uuid.UUID = Field(description="匹配结果唯一标识")
    resume_id: uuid.UUID = Field(description="简历 ID")
    job_id: uuid.UUID = Field(description="岗位 ID")

    # Scores
    rule_score: float | None = Field(default=None, description="规则匹配得分 (0-10)")
    tfidf_score: float | None = Field(default=None, description="TF-IDF 匹配得分 (0-10)")
    semantic_score: float | None = Field(default=None, description="语义匹配得分 (0-10)")
    llm_score: float | None = Field(default=None, description="LLM 推理得分 (0-10)")
    overall_score: float = Field(description="加权综合得分 (0-10)")

    # Details
    dimension_scores: DimensionScores = Field(description="7 维度详细评分")
    matched_skills: list[str] = Field(default_factory=list, description="匹配的技能列表")
    missing_skills: list[str] = Field(default_factory=list, description="缺失的必备技能")
    llm_reasoning: str | None = Field(default=None, description="LLM 生成的匹配理由")
    suggestions: list[str] = Field(default_factory=list, description="ATS 优化建议")

    # Hard filters
    is_hard_pass: bool = Field(default=False, description="是否被硬性条件淘汰")
    hard_pass_reasons: list[str] = Field(default_factory=list, description="硬性淘汰原因")

    # Meta
    match_duration_ms: int | None = Field(default=None, description="匹配耗时（毫秒）")
    created_at: datetime = Field(description="匹配时间")

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
