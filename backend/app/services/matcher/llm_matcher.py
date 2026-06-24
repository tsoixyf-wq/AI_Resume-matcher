"""
Stage 4: LLM-based deep reasoning for resume-job matching.
Generates human-readable explanations for match/non-match decisions.
"""

from typing import AsyncIterator

import structlog

from app.schemas.job import ParsedJDData
from app.schemas.resume import ParsedResumeData
from app.utils.llm_client import LLMClient

logger = structlog.get_logger(__name__)

MATCHING_SYSTEM_PROMPT = """你是一位拥有15年经验的资深招聘专家和技术面试官。
你的任务是对候选人与岗位要求的匹配程度进行深度分析，并给出专业、可解释的评估报告。

分析要点：
1. 不要只看关键词匹配，要理解技术之间的关联性和可迁移性
2. 对于每项匹配或不匹配，都要给出具体的理由
3. 评分要客观严谨，参考行业标准
4. 给出的建议要具体、可操作
5. 用中文回答"""


class LLMMatcher:
    """LLM-powered deep matching with reasoning and suggestions."""

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or LLMClient()

    async def match(
        self,
        resume: ParsedResumeData,
        jd: ParsedJDData,
        previous_scores: dict | None = None,
    ) -> dict:
        """
        Returns:
            {
                "score": float (0-10),
                "dimension_scores": {
                    "education": float,
                    "skills": float,
                    "experience": float,
                    "overall": float
                },
                "reasoning": str,
                "matched_skills": list[str],
                "missing_skills": list[str],
                "suggestions": list[str],
            }
        """
        # Build the prompt
        resume_summary = self._format_resume(resume)
        jd_summary = self._format_jd(jd)
        previous_context = ""
        if previous_scores:
            previous_context = f"\n前几轮自动匹配的参考分数：{previous_scores}\n"

        prompt = f"""请对以下候选人和岗位进行深度匹配分析：

## 岗位要求
{jd_summary}

## 候选人简历
{resume_summary}

{previous_context}
请从以下维度逐项深度分析，并给出 0-10 分的评分：

### 1. 学历匹配
- 分析候选人的学历、专业是否与岗位要求匹配
- 知名院校或相关专业可适当加分

### 2. 技能匹配
- 列出候选人具备的与岗位要求匹配的技能
- 列出岗位要求但候选人缺失的关键技能
- 分析技能之间的可迁移性（如：会 PyTorch 的人通常能快速上手 TensorFlow）

### 3. 经验匹配
- 分析候选人的工作和项目经验与岗位职责的相关性
- 评估经验的深度和广度

### 4. 证书匹配（新增）
- 分析候选人持有的专业证书与岗位要求的匹配度
- 评估证书的含金量和行业认可度
- 如无证书相关信息，给出合理评分（建议 5.0 中性分）

### 5. 语言能力（新增）
- 评估候选人的语言能力（英语四六级、雅思托福、其他外语等）是否满足岗位要求
- 如岗位描述未提及语言要求，给出中性分 5.0

### 6. 地点匹配（新增）
- 分析候选人所在城市与岗位地点的匹配度
- 异地求职可适当降低评分
- 如无地点信息，给出中性分 5.0

### 7. 综合评估
- 总体匹配度评分
- 候选人相对于该岗位的优势和不足
- 3-5 条具体的简历优化建议

请以 JSON 格式返回结果，格式如下：
{{
  "education_score": 8.5,
  "education_reasoning": "学历匹配的分析理由...",
  "skills_score": 7.0,
  "skills_reasoning": "技能匹配的分析理由...",
  "matched_skills": ["Python", "FastAPI", "PostgreSQL"],
  "missing_skills": ["Kubernetes", "Kafka"],
  "experience_score": 6.5,
  "experience_reasoning": "经验匹配的分析理由...",
  "certifications_score": 6.0,
  "certifications_reasoning": "证书匹配的分析理由...",
  "languages_score": 7.0,
  "languages_reasoning": "语言能力的分析理由...",
  "location_score": 8.0,
  "location_reasoning": "地点匹配的分析理由...",
  "overall_score": 7.3,
  "overall_reasoning": "综合评价...",
  "suggestions": [
    "建议补充 Kubernetes 相关项目经验",
    "简历中可以量化工作成果，增加数据指标"
  ]
}}"""

        result = await self.llm.chat_with_json_output(
            prompt=prompt,
            system_prompt=MATCHING_SYSTEM_PROMPT,
            temperature=0.2,
        )

        if result.get("parse_error"):
            logger.warning("LLM matching JSON parse failed, using raw output")
            return {
                "score": 5.0,
                "dimension_scores": {
                    "education": 5.0,
                    "skills": 5.0,
                    "experience": 5.0,
                    "certifications": 5.0,
                    "languages": 5.0,
                    "location": 5.0,
                    "overall": 5.0,
                },
                "reasoning": result.get("raw_output", ""),
                "matched_skills": [],
                "missing_skills": [],
                "suggestions": [],
            }

        return {
            "score": result.get("overall_score", 5.0),
            "dimension_scores": {
                "education": result.get("education_score", 5.0),
                "skills": result.get("skills_score", 5.0),
                "experience": result.get("experience_score", 5.0),
                "certifications": result.get("certifications_score", 5.0),
                "languages": result.get("languages_score", 5.0),
                "location": result.get("location_score", 5.0),
                "overall": result.get("overall_score", 5.0),
            },
            "reasoning": self._build_reasoning_text(result),
            "matched_skills": result.get("matched_skills", []),
            "missing_skills": result.get("missing_skills", []),
            "suggestions": result.get("suggestions", []),
        }

    async def match_stream(
        self,
        resume: ParsedResumeData,
        jd: ParsedJDData,
    ) -> AsyncIterator[str]:
        """Stream the LLM matching analysis token by token."""
        resume_summary = self._format_resume(resume)
        jd_summary = self._format_jd(jd)

        prompt = f"""请对以下候选人和岗位进行深度匹配分析，用流畅的中文逐维度分析：

## 岗位要求
{jd_summary}

## 候选人简历
{resume_summary}

请从学历匹配、技能匹配、经验匹配、综合评价四个维度逐一深入分析。"""

        messages = [
            {"role": "system", "content": MATCHING_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        async for token in self.llm.chat_stream(messages, temperature=0.3):
            yield token

    def _format_resume(self, resume: ParsedResumeData) -> str:
        """Format resume data for the LLM prompt."""
        lines = []

        bi = resume.basic_info
        lines.append(f"姓名: {bi.name}")
        if bi.email:
            lines.append(f"邮箱: {bi.email}")
        if bi.years_of_experience is not None:
            lines.append(f"工作年限: {bi.years_of_experience}年")

        if resume.education:
            lines.append("\n教育背景:")
            for edu in resume.education:
                line = f"- {edu.school} | {edu.major} | {edu.degree}"
                if edu.start_date:
                    line += f" | {edu.start_date} - {edu.end_date or '至今'}"
                lines.append(line)

        if resume.skills:
            lines.append("\n技能:")
            for skill in resume.skills:
                level = f" ({skill.level})" if skill.level else ""
                lines.append(f"- {skill.name}{level}")

        if resume.work_experience:
            lines.append("\n工作/实习经历:")
            for exp in resume.work_experience:
                lines.append(f"- {exp.title} @ {exp.company}")
                if exp.description:
                    lines.append(f"  描述: {exp.description[:200]}")

        if resume.projects:
            lines.append("\n项目经历:")
            for proj in resume.projects:
                lines.append(f"- {proj.name}")
                if proj.description:
                    lines.append(f"  描述: {proj.description[:200]}")
                if proj.tech_stack:
                    lines.append(f"  技术栈: {', '.join(proj.tech_stack)}")

        if resume.certifications:
            lines.append("\n证书:")
            for cert in resume.certifications:
                issuer = f" ({cert.issuer})" if cert.issuer else ""
                date = f" - {cert.date}" if cert.date else ""
                lines.append(f"- {cert.name}{issuer}{date}")

        if resume.languages:
            lines.append("\n语言能力:")
            for lang in resume.languages:
                prof = f" ({lang.proficiency})" if lang.proficiency else ""
                lines.append(f"- {lang.name}{prof}")

        if resume.competitions:
            lines.append("\n竞赛获奖:")
            for comp in resume.competitions:
                award = f" - {comp.award}" if comp.award else ""
                level = f" [{comp.level}]" if comp.level else ""
                lines.append(f"- {comp.name}{level}{award}")

        return "\n".join(lines)

    def _format_jd(self, jd: ParsedJDData) -> str:
        """Format JD data for the LLM prompt."""
        lines = []

        title = jd.basic_info.get("title", "未知岗位")
        lines.append(f"岗位: {title}")
        if jd.basic_info.get("department"):
            lines.append(f"部门: {jd.basic_info['department']}")
        if jd.basic_info.get("location"):
            lines.append(f"地点: {jd.basic_info['location']}")

        if jd.skills_required:
            lines.append("\n技能要求:")
            for skill in jd.skills_required:
                importance = f" [{skill.importance}]" if skill.importance else ""
                level = f" ({skill.level})" if skill.level else ""
                lines.append(f"- {skill.name}{level}{importance}")

        if jd.requirements:
            lines.append("\n岗位要求:")
            for req in jd.requirements:
                req_type = "【必须】" if req.type == "must" else "【加分】"
                lines.append(f"- {req_type} {req.description}")

        if jd.responsibilities:
            lines.append("\n岗位职责:")
            for resp in jd.responsibilities:
                lines.append(f"- {resp}")

        if jd.education_required.min_degree:
            lines.append(f"\n学历要求: {jd.education_required.min_degree}及以上")

        if jd.experience_required.min_years:
            lines.append(f"经验要求: {jd.experience_required.min_years}年以上")
        if jd.experience_required.preferred_fields:
            lines.append(f"优先领域: {', '.join(jd.experience_required.preferred_fields)}")

        return "\n".join(lines)

    @staticmethod
    def _build_reasoning_text(result: dict) -> str:
        """Build a combined reasoning text from the LLM results."""
        sections = []

        if result.get("education_reasoning"):
            sections.append(f"【学历匹配】\n{result['education_reasoning']}")
        if result.get("skills_reasoning"):
            sections.append(f"【技能匹配】\n{result['skills_reasoning']}")
        if result.get("experience_reasoning"):
            sections.append(f"【经验匹配】\n{result['experience_reasoning']}")
        if result.get("certifications_reasoning"):
            sections.append(f"【证书匹配】\n{result['certifications_reasoning']}")
        if result.get("languages_reasoning"):
            sections.append(f"【语言能力】\n{result['languages_reasoning']}")
        if result.get("location_reasoning"):
            sections.append(f"【地点匹配】\n{result['location_reasoning']}")
        if result.get("overall_reasoning"):
            sections.append(f"【综合评估】\n{result['overall_reasoning']}")

        return "\n\n".join(sections)
