"""Pydantic schemas for Resume."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# --- Sub-schemas for parsed resume data ---

class BasicInfo(BaseModel):
    name: str = Field(default="", description="候选人姓名")
    email: str = Field(default="", description="邮箱")
    phone: str = Field(default="", description="电话")
    city: str = Field(default="", description="所在城市")
    years_of_experience: float | None = Field(default=None, description="工作年限")


class Education(BaseModel):
    school: str = Field(default="", description="学校名称")
    degree: str = Field(default="", description="学位（本科/硕士/博士）")
    major: str = Field(default="", description="专业")
    start_date: str | None = Field(default=None, description="入学时间")
    end_date: str | None = Field(default=None, description="毕业时间")
    expected_graduation: str | None = Field(
        default=None, description="预计毕业时间（校招生适用）"
    )
    gpa: float | None = Field(default=None, description="GPA")


class Competition(BaseModel):
    """Competition/award entry — primarily for campus resumes."""
    name: str = Field(default="", description="竞赛/奖项名称")
    level: str = Field(default="", description="级别：国际/全国/省/校")
    award: str = Field(default="", description="获奖情况")
    date: str | None = Field(default=None, description="获奖日期")


class WorkExperience(BaseModel):
    company: str = Field(default="", description="公司名称")
    title: str = Field(default="", description="职位")
    start_date: str | None = Field(default=None, description="入职时间")
    end_date: str | None = Field(default=None, description="离职时间")
    description: str = Field(default="", description="工作描述")
    achievements: list[str] = Field(default_factory=list, description="工作成就")
    employment_type: str = Field(
        default="full-time",
        description="雇佣类型: full-time / internship / part-time / contract",
    )


class Skill(BaseModel):
    name: str = Field(..., description="技能名称")
    level: str | None = Field(default=None, description="掌握程度（初级/中级/高级/精通）")
    category: str | None = Field(
        default=None, description="技能分类（编程语言/框架/工具/软技能）"
    )


class Project(BaseModel):
    name: str = Field(default="", description="项目名称")
    description: str = Field(default="", description="项目描述")
    tech_stack: list[str] = Field(default_factory=list, description="技术栈")
    url: str | None = Field(default=None, description="项目链接")


class Certification(BaseModel):
    name: str = Field(default="", description="证书名称")
    issuer: str = Field(default="", description="颁发机构")
    date: str | None = Field(default=None, description="获得日期")


class Language(BaseModel):
    name: str = Field(default="", description="语言名称")
    proficiency: str = Field(default="", description="熟练程度")


class ParsedResumeData(BaseModel):
    """Structured data extracted from a resume."""
    resume_type: str = Field(
        default="unknown",
        description="简历类型: campus / experienced / unknown",
    )
    basic_info: BasicInfo = Field(default_factory=BasicInfo)
    education: list[Education] = Field(default_factory=list)
    work_experience: list[WorkExperience] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)
    competitions: list[Competition] = Field(
        default_factory=list, description="竞赛获奖（校招生重点）"
    )


# --- API schemas ---

class ResumeUploadResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    file_type: str
    parse_status: str
    resume_type: str = "unknown"
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeDetailResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    file_type: str
    parsed_data: ParsedResumeData
    raw_text: str
    parse_status: str
    parse_error: str | None = None
    parse_duration_ms: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeListResponse(BaseModel):
    items: list[ResumeUploadResponse]
    total: int
    page: int
    page_size: int
