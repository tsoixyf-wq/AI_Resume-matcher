"""
Resume type classifier — detects whether a resume is from a campus/fresh-grad
candidate or an experienced professional.

Detection is rule-based (fast, no LLM cost) with LLM fallback for ambiguous cases.
"""

import re
from datetime import datetime

import structlog

from app.schemas.resume import ParsedResumeData

logger = structlog.get_logger(__name__)

# Keywords strongly indicating campus/fresh-grad resumes
CAMPUS_KEYWORDS = [
    "应届", "毕业生", "校园", "实习", "在读", "预计毕业",
    "本科在读", "硕士在读", "博士在读", "fresh grad", "fresh graduate",
    "campus", "internship", "intern", "graduating",
    "GPA", "年级排名", "奖学金", "学生干部", "社团",
    "暑期实习", "寒假实习", "毕业设计", "毕业论文",
]

# Keywords strongly indicating experienced resumes
EXPERIENCED_KEYWORDS = [
    "多年经验", "资深", "高级", "主管", "经理", "总监",
    "团队管理", "带队", "负责", "senior", "staff", "lead",
    "manager", "director", "principal",
]


def classify_resume(
    parsed: ParsedResumeData,
    raw_text: str,
) -> str:
    """
    Classify resume as 'campus', 'experienced', or 'unknown'.

    Uses a cascade of heuristics:
    1. years_of_experience >= 3 with work entries → experienced
    2. graduation not yet happened + low/no experience → campus
    3. Keyword density check on raw_text
    4. Fallback to 'unknown' (LLM can override during extraction)
    """
    text_lower = raw_text.lower()

    # Heuristic 1: Strong experience signal
    years = parsed.basic_info.years_of_experience or 0
    has_work = len(parsed.work_experience) > 0
    has_fulltime = any(
        w.employment_type == "full-time" for w in parsed.work_experience
    )

    if years >= 3 and has_fulltime:
        logger.debug("Classified as experienced", reason="years>=3 + fulltime work")
        return "experienced"

    # Heuristic 2: Education-based — recent or future graduation
    for edu in parsed.education:
        if edu.expected_graduation:
            logger.debug("Classified as campus", reason="expected_graduation present")
            return "campus"
        if edu.end_date:
            try:
                # Parse end_date in YYYY or YYYY-MM format
                end_str = edu.end_date.strip()
                if len(end_str) >= 4:
                    end_year = int(end_str[:4])
                    current_year = datetime.now().year
                    if end_year >= current_year - 1:
                        # Graduated within last year or in the future
                        if not has_fulltime and years < 2:
                            logger.debug(
                                "Classified as campus",
                                reason=f"recent graduation {end_year}",
                            )
                            return "campus"
            except (ValueError, IndexError):
                pass

    # Heuristic 3: Keyword density
    campus_count = sum(
        1 for kw in CAMPUS_KEYWORDS if kw.lower() in text_lower
    )
    experienced_count = sum(
        1 for kw in EXPERIENCED_KEYWORDS if kw.lower() in text_lower
    )

    if campus_count >= 2 and experienced_count == 0:
        logger.debug("Classified as campus", reason=f"campus_kw={campus_count}")
        return "campus"
    if experienced_count >= 3 and campus_count == 0:
        logger.debug(
            "Classified as experienced", reason=f"experienced_kw={experienced_count}"
        )
        return "experienced"

    # Heuristic 4: Internships but no full-time work
    has_internships = any(
        w.employment_type == "internship" for w in parsed.work_experience
    )
    if has_internships and not has_fulltime and years < 2:
        logger.debug("Classified as campus", reason="internships only, no fulltime")
        return "campus"

    # Heuristic 5: Very low experience
    if years == 0 and not has_work and parsed.education:
        logger.debug("Classified as campus", reason="no experience + has education")
        return "campus"

    logger.debug("Could not classify, returning unknown")
    return "unknown"
