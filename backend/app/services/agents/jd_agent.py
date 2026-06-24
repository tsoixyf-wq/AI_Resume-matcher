"""JD Analysis Agent - extracts structured requirements from raw job descriptions."""

import structlog

from app.schemas.job import (
    EducationRequirement,
    ExperienceRequirement,
    ParsedJDData,
    Requirement,
    SkillRequirement,
)
from app.services.agents.state import MatchingState
from app.services.parser.llm_extractor import LLMExtractor

logger = structlog.get_logger(__name__)


async def jd_analyze_agent(state: MatchingState) -> MatchingState:
    """
    Agent that parses a raw JD text into structured requirements.
    Uses LLM for deep semantic extraction.
    """
    jd_text = state.get("jd_text", "")
    if not jd_text:
        state["error"] = "岗位描述文本为空"
        return state

    try:
        llm_extractor = LLMExtractor()
        jd_data = await llm_extractor.extract_jd(jd_text)

        if jd_data and not jd_data.get("parse_error"):
            parsed = ParsedJDData(**jd_data)
        else:
            # Fallback: minimal parsing
            parsed = ParsedJDData(
                basic_info={"title": "未知岗位"},
                skills_required=[],
                requirements=[],
            )

        state["jd_parsed"] = parsed
        logger.info(
            "JD analysis completed",
            title=parsed.basic_info.get("title", ""),
            skills_count=len(parsed.skills_required),
        )

    except Exception as e:
        logger.error("JD analysis failed", error=str(e))
        state["error"] = f"岗位描述解析失败: {str(e)}"

    return state
