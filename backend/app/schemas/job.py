"""Pydantic schemas for Job Description."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# --- Sub-schemas for parsed JD data ---

class Requirement(BaseModel):
    type: str = Field(default="must", description="要求类型: must / preferred")
    category: str = Field(default="", description="要求分类")
    description: str = Field(default="", description="具体要求描述")
    weight: float = Field(default=1.0, description="权重")


class SkillRequirement(BaseModel):
    name: str = Field(..., description="技能名称")
    level: str | None = Field(default=None, description="要求等级")
    importance: str = Field(
        default="required",
        description="重要程度: required / preferred / nice-to-have",
    )


class EducationRequirement(BaseModel):
    min_degree: str | None = Field(default=None, description="最低学历要求")
    preferred_majors: list[str] = Field(default_factory=list, description="优先专业")


class ExperienceRequirement(BaseModel):
    min_years: float | None = Field(default=None, description="最低工作年限")
    preferred_fields: list[str] = Field(default_factory=list, description="优先领域")


class ParsedJDData(BaseModel):
    """Structured data extracted from a job description."""
    basic_info: dict = Field(default_factory=dict, description="基本信息（标题/部门/地点/薪资）")
    requirements: list[Requirement] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    skills_required: list[SkillRequirement] = Field(default_factory=list)
    education_required: EducationRequirement = Field(default_factory=EducationRequirement)
    experience_required: ExperienceRequirement = Field(default_factory=ExperienceRequirement)


# --- API schemas ---

class JDCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="岗位名称")
    department: str | None = Field(default=None, description="部门")
    location: str | None = Field(default=None, description="工作地点")
    raw_text: str = Field(..., min_length=1, description="岗位描述全文")


class JDResponse(BaseModel):
    id: uuid.UUID
    title: str
    department: str | None = None
    location: str | None = None
    parsed_data: ParsedJDData
    raw_text: str
    parse_status: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class JDListResponse(BaseModel):
    items: list[JDResponse]
    total: int
    page: int
    page_size: int
