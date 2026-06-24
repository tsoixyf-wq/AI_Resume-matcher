"""
Stage 2: TF-IDF + Fuzzy matching.
Computes keyword coverage and fuzzy skill name matching.
"""

import re

import jieba
import structlog
from fuzzywuzzy import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.schemas.job import ParsedJDData
from app.schemas.resume import ParsedResumeData

logger = structlog.get_logger(__name__)


class TFIDFMatcher:
    """TF-IDF based keyword coverage and fuzzy skill matching."""

    def __init__(self):
        self._vectorizer: TfidfVectorizer | None = None
        self._stopwords = set()

    async def match(self, resume: ParsedResumeData, jd: ParsedJDData) -> dict:
        """
        Returns:
            {
                "score": float (0-10),
                "tfidf_similarity": float (0-1),
                "skill_coverage": float (0-1),
                "matched_skills": list[dict],
                "details": dict
            }
        """
        # Build text representations
        resume_text = self._build_resume_text(resume)
        jd_text = self._build_jd_text(jd)

        # 1. TF-IDF cosine similarity
        tfidf_sim = self._compute_tfidf_similarity(resume_text, jd_text)

        # 2. Skill-level fuzzy matching
        skill_result = self._fuzzy_skill_match(resume, jd)

        # 3. Combined score
        combined_score = (tfidf_sim * 0.4 + skill_result["coverage"] * 0.6) * 10

        return {
            "score": round(combined_score, 2),
            "tfidf_similarity": round(tfidf_sim, 4),
            "skill_coverage": round(skill_result["coverage"], 4),
            "matched_skills": skill_result["matched"],
            "details": {
                "tfidf_weight": 0.4,
                "skill_weight": 0.6,
            },
        }

    def _build_resume_text(self, resume: ParsedResumeData) -> str:
        """Build a text representation from parsed resume data."""
        parts = []

        if resume.basic_info.name:
            parts.append(resume.basic_info.name)

        for skill in resume.skills:
            parts.append(skill.name)

        for exp in resume.work_experience:
            parts.append(f"{exp.title} {exp.company} {exp.description}")
            parts.extend(exp.achievements)

        for edu in resume.education:
            parts.append(f"{edu.school} {edu.major} {edu.degree}")

        for proj in resume.projects:
            parts.append(f"{proj.name} {proj.description}")
            parts.extend(proj.tech_stack)

        return " ".join(parts)

    def _build_jd_text(self, jd: ParsedJDData) -> str:
        """Build a text representation from parsed JD data."""
        parts = []

        parts.append(jd.basic_info.get("title", ""))

        for req in jd.requirements:
            parts.append(req.description)

        parts.extend(jd.responsibilities)

        for skill in jd.skills_required:
            parts.append(skill.name)

        return " ".join(parts)

    def _compute_tfidf_similarity(self, text1: str, text2: str) -> float:
        """Compute TF-IDF cosine similarity between two texts."""
        if not text1.strip() or not text2.strip():
            return 0.0

        # Use jieba for Chinese word segmentation
        seg1 = " ".join(jieba.cut(text1))
        seg2 = " ".join(jieba.cut(text2))

        try:
            vectorizer = TfidfVectorizer(max_features=5000)
            tfidf_matrix = vectorizer.fit_transform([seg1, seg2])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
            return float(similarity[0][0])
        except Exception as e:
            logger.warning("TF-IDF computation failed", error=str(e))
            return 0.0

    def _fuzzy_skill_match(self, resume: ParsedResumeData, jd: ParsedJDData) -> dict:
        """Match skills using fuzzy string matching."""
        jd_skills = [s.name.lower() for s in jd.skills_required]
        resume_skills = [s.name.lower() for s in resume.skills]

        if not jd_skills:
            return {"coverage": 1.0, "matched": []}

        matched = []
        for jd_skill in jd_skills:
            best_score = 0
            best_match = None
            for rs in resume_skills:
                score = max(
                    fuzz.ratio(jd_skill, rs),
                    fuzz.partial_ratio(jd_skill, rs),
                    fuzz.token_sort_ratio(jd_skill, rs),
                )
                if score > best_score:
                    best_score = score
                    best_match = rs
            if best_score >= 75 and best_match:
                matched.append({
                    "jd_skill": jd_skill,
                    "resume_skill": best_match,
                    "fuzzy_score": best_score,
                })

        coverage = len(matched) / len(jd_skills) if jd_skills else 1.0
        return {"coverage": coverage, "matched": matched}
