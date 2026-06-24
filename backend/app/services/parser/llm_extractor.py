"""
LLM-assisted resume information extraction.
Used as a fallback for complex/ambiguous cases that regex and NER can't handle.
"""

from app.schemas.resume import ParsedResumeData
from app.utils.llm_client import LLMClient


RESUME_EXTRACTION_SYSTEM_PROMPT = """你是一位专业的简历信息提取专家。你的任务是从简历文本中提取结构化信息。
You are also capable of processing English resumes — use the same structured output format.

请严格按照以下规则提取 / Please follow these extraction rules:
1. 基本信息/Basic Info：姓名/Name、邮箱/Email、电话/Phone、所在城市/City、工作年限/Years of Experience
2. 教育经历/Education：学校全称/School、学位/Degree、专业/Major、入学时间/Start Date、毕业时间/End Date、预计毕业时间/Expected Graduation (应届生/fresh grads)、GPA
3. 工作经历/Work Experience：公司全称/Company、职位/Title、起止时间/Dates、工作描述和成就/Description & Achievements、雇佣类型/Employment Type (full-time/internship/part-time/contract)
   - 实习经历设置 employment_type="internship" / Internships → employment_type="internship"
   - 全职工作设置 employment_type="full-time" / Full-time → employment_type="full-time"
4. 技能/Skills：技能名称/Name、掌握程度/Level（初级/Beginner 中级/Intermediate 高级/Advanced 精通/Expert）、分类/Category（编程语言/Programming 框架/Framework 数据库/Database 工具/Tools 云平台/Cloud 软技能/Soft Skills 其他/Other）
5. 项目经历/Projects：项目名称/Name、描述/Description、技术栈/Tech Stack、链接/URL
6. 竞赛获奖/Competitions：竞赛名称/Name、级别/Level（国际/International 全国/National 省/Provincial 校/School）、获奖情况/Award、日期/Date
7. 证书/Certifications 和 语言能力/Languages

校招简历/Fresh-grad Resumes：
- 实习经历填入 work_experience，employment_type="internship"
- 预计毕业时间填入 education[].expected_graduation
- 竞赛获奖、奖学金等填入 competitions
- GPA 务必提取
- 项目经历是核心评估依据

社招简历/Experienced Resumes：
- 重点提取工作成就和量化成果 / Focus on achievements and quantified results
- employment_type="full-time"
- 管理经验、团队规模重点提取

通用/General：
- 未出现的信息使用空字符串或空数组 / Missing info → empty string or []
- 日期格式 YYYY-MM 或 YYYY / Date format: YYYY-MM or YYYY
- 技能名称保持原文写法 / Keep skill names as written
- 英文简历的 section 标题可能是 Experience, Education, Skills 等"""


class LLMExtractor:
    """Use LLM for deep semantic extraction of resume fields."""

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or LLMClient()

    async def extract(self, resume_text: str) -> ParsedResumeData:
        """Extract structured resume data using LLM.

        Args:
            resume_text: Raw text of the resume.

        Returns:
            Structured ParsedResumeData object.
        """
        # Build the extraction prompt
        prompt = f"""请从以下简历文本中提取结构化信息：

---
{resume_text[:8000]}
---

请提取并返回完整的 JSON 结构化信息。"""

        result = await self.llm.chat_with_json_output(
            prompt=prompt,
            output_schema=ParsedResumeData,
            system_prompt=RESUME_EXTRACTION_SYSTEM_PROMPT,
            temperature=0.0,
        )

        # Handle parse failures gracefully
        if result.get("parse_error"):
            return ParsedResumeData()
        return ParsedResumeData(**result)

    async def extract_jd(self, jd_text: str) -> dict:
        """Extract structured job description data using LLM."""
        from app.schemas.job import ParsedJDData

        system_prompt = """你是一位专业的招聘需求分析师。请从岗位描述中提取结构化信息。
包括：基本要求、加分项、技能要求、学历要求、经验要求、岗位职责等。"""

        prompt = f"""请分析以下岗位描述，提取结构化信息：

---
{jd_text[:6000]}
---

请返回完整的 JSON 结构化信息，区分"必须要求"和"优先条件"。"""

        result = await self.llm.chat_with_json_output(
            prompt=prompt,
            output_schema=ParsedJDData,
            system_prompt=system_prompt,
            temperature=0.0,
        )

        if result.get("parse_error"):
            return {}
        return result
