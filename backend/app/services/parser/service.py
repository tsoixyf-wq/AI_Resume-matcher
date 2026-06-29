"""Resume parsing service — single source of truth for the parse pipeline.

Used by both the dev-mode synchronous upload path (api/resumes.py) and the
Celery async parse task (tasks/matching_tasks.py) to avoid logic duplication.

Pipeline: document load → NER (always) → LLM (best-effort) → merge →
skill normalize → classify.
"""

import logging
import time
from dataclasses import dataclass

from app.schemas.resume import (
    BasicInfo,
    Education,
    ParsedResumeData,
    Skill,
    WorkExperience,
)
from app.services.parser.llm_extractor import LLMExtractor
from app.services.parser.ner_extractor import NERExtractor
from app.services.parser.resume_classifier import classify_resume
from app.services.parser.skill_normalizer import SkillNormalizer

logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    """Outcome of a resume parse operation."""

    parsed: ParsedResumeData
    llm_error: str | None = None  # non-None when LLM failed and NER fallback was used
    duration_ms: int = 0


class ResumeParserService:
    """Encapsulates the full resume parse pipeline (text → structured data)."""

    async def parse(self, text: str) -> ParseResult:
        """Parse resume text into structured ``ParsedResumeData``.

        Always returns a ``ParseResult``; LLM failures fall back to NER-only
        extraction and are reported via ``ParseResult.llm_error``.
        """
        start = time.time()
        llm_error: str | None = None

        # Tier 1: NER extraction (always works, no external API)
        ner = NERExtractor()
        entities = await ner.extract(text)

        # Tier 2: LLM deep extraction (may fail if API key is invalid)
        try:
            parsed = await LLMExtractor().extract(text)
        except Exception as llm_err:
            logger.warning("LLM extraction failed, falling back to NER-only: %s", llm_err)
            llm_error = str(llm_err)[:300]
            parsed = self._ner_fallback(entities)

        # Merge NER high-confidence fields (priority over LLM results)
        if entities.get("email") and not parsed.basic_info.email:
            parsed.basic_info.email = entities["email"]
        if entities.get("phone") and not parsed.basic_info.phone:
            parsed.basic_info.phone = entities["phone"]
        if entities.get("name") and not parsed.basic_info.name:
            parsed.basic_info.name = entities["name"]

        # Normalize skills (NER + LLM combined, dedup)
        normalizer = SkillNormalizer()
        normalized = normalizer.normalize_list(
            entities.get("skills", []) + [s.name for s in parsed.skills]
        )
        seen: set[str] = set()
        merged: list[Skill] = []
        for s in normalized:
            if s["name"].lower() not in seen:
                seen.add(s["name"].lower())
                merged.append(Skill(name=s["name"], category=s.get("category_display")))
        parsed.skills = merged

        # Classify resume type (campus vs experienced)
        parsed.resume_type = classify_resume(parsed, text)

        duration_ms = int((time.time() - start) * 1000)
        logger.info(
            "Resume parsed in %dms, type=%s", duration_ms, parsed.resume_type
        )
        return ParseResult(parsed=parsed, llm_error=llm_error, duration_ms=duration_ms)

    @staticmethod
    def _ner_fallback(entities: dict) -> ParsedResumeData:
        """Build a ``ParsedResumeData`` from NER entities when LLM is unavailable.

        Covers email, phone, name, skills, schools and companies — enough for
        basic matching. Education, work experience and projects are populated
        from NER entities where available.
        """
        skills = [Skill(name=s, category="") for s in entities.get("skills", [])]
        education = [Education(school=s) for s in entities.get("schools", [])]
        work = [WorkExperience(company=c) for c in entities.get("companies", [])]

        return ParsedResumeData(
            basic_info=BasicInfo(
                name=entities.get("name", ""),
                email=entities.get("email", ""),
                phone=entities.get("phone", ""),
            ),
            education=education,
            work_experience=work,
            skills=skills,
        )
