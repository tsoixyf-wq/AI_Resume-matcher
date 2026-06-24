"""Resume Parsing Agent - extracts structured information from raw resume text."""

import structlog

from app.services.agents.state import MatchingState
from app.services.parser.llm_extractor import LLMExtractor
from app.services.parser.ner_extractor import NERExtractor
from app.services.parser.resume_classifier import classify_resume
from app.services.parser.skill_normalizer import SkillNormalizer
from app.schemas.resume import (
    BasicInfo,
    Education,
    ParsedResumeData,
    Skill,
    WorkExperience,
)

logger = structlog.get_logger(__name__)


async def resume_parse_agent(state: MatchingState) -> MatchingState:
    """
    Agent that parses a raw resume text into structured data.
    Uses a three-tier strategy: regex → NER → LLM.
    """
    resume_text = state.get("resume_text", "")
    if not resume_text:
        state["error"] = "简历文本为空"
        return state

    try:
        # Tier 1: Regex-based NER extraction
        ner_extractor = NERExtractor()
        entities = await ner_extractor.extract(resume_text)
        logger.info("NER extraction completed", entities_count=len(entities.get("skills", [])))

        # Tier 2: Skill normalization
        normalizer = SkillNormalizer()
        normalized_skills = normalizer.normalize_list(entities.get("skills", []))

        # Tier 3: LLM deep extraction for complex fields
        llm_extractor = LLMExtractor()
        parsed = await llm_extractor.extract(resume_text)

        # Merge NER results into parsed data (NER for fast/accurate email, phone, URL)
        if entities.get("email"):
            parsed.basic_info.email = entities["email"]
        if entities.get("phone"):
            parsed.basic_info.phone = entities["phone"]
        if entities.get("name") and not parsed.basic_info.name:
            parsed.basic_info.name = entities["name"]

        # Supplement skills from NER
        llm_skill_names = {s.name.lower() for s in parsed.skills}
        for skill_dict in normalized_skills:
            if skill_dict["name"].lower() not in llm_skill_names:
                parsed.skills.append(Skill(
                    name=skill_dict["name"],
                    category=skill_dict.get("category_display"),
                ))

        # Classify resume type (campus vs experienced)
        parsed.resume_type = classify_resume(parsed, resume_text)

        state["resume_parsed"] = parsed
        logger.info(
            "Resume parsing completed",
            name=parsed.basic_info.name,
            resume_type=parsed.resume_type,
        )

    except Exception as e:
        logger.error("Resume parsing failed", error=str(e))
        state["error"] = f"简历解析失败: {str(e)}"

    return state
